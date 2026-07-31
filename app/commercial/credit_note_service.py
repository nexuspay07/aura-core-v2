"""Lifecycle and exact-money management for the credit-note aggregate."""

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.commercial.billing import BillingError, BillingPersistenceConflictError
from app.commercial.invoice_service import InvoiceNotFoundError
from app.commercial.models import CreditNote, CreditNoteLineItem
from app.commercial.repositories import (
    CreditNoteRepository,
    InvoiceRepository,
    SqlAlchemyCreditNoteRepository,
    SqlAlchemyInvoiceRepository,
)


_ZERO = Decimal("0.0000")
_QUANTUM = Decimal("0.0001")


class CreditNoteService:
    """Mutates draft credit notes in the caller-owned SQLAlchemy transaction."""

    def __init__(
        self,
        session: Session,
        *,
        credit_note_repository: CreditNoteRepository | None = None,
        invoice_repository: InvoiceRepository | None = None,
        clock=lambda: datetime.now(timezone.utc),
    ):
        self.session = session
        self.credit_notes = credit_note_repository or SqlAlchemyCreditNoteRepository(session)
        self.invoices = invoice_repository or SqlAlchemyInvoiceRepository(session)
        self.clock = clock

    def create_draft(self, *, organization_id, invoice_id, credit_note_number, currency, reason=None) -> CreditNote:
        self._id(organization_id, "organization_id"); self._id(invoice_id, "invoice_id")
        self._nonblank(credit_note_number, "credit_note_number"); self._currency(currency)
        if reason is not None and not isinstance(reason, str): self._invalid("reason must be a string or None.")
        invoice = self._invoice(invoice_id)
        if invoice.organization_id != organization_id: self._invalid("Invoice does not belong to organization.")
        if invoice.currency != currency: self._invalid("Credit note currency does not match invoice currency.")
        now = self._now()
        note = CreditNote(
            organization_id=organization_id, invoice_id=invoice_id, credit_note_number=credit_note_number,
            status="draft", currency=currency, reason=reason, subtotal=_ZERO, tax=_ZERO, total=_ZERO,
            amount_applied=_ZERO, amount_remaining=_ZERO, issued_at=None, voided_at=None,
            created_at=now, updated_at=now, version=1,
        )
        return self.credit_notes.save(note)

    def add_line_item(self, credit_note_id, *, description, quantity, unit_amount, tax=Decimal("0")) -> CreditNoteLineItem:
        note = self._draft(credit_note_id)
        self._nonblank(description, "description")
        quantity = self._positive_decimal(quantity, "quantity")
        unit_amount = self._nonnegative_decimal(unit_amount, "unit_amount")
        tax = self._nonnegative_decimal(tax, "tax")
        subtotal = self._money(quantity * unit_amount)
        total = self._money(subtotal + tax)
        line_number = max((line.line_number for line in note.line_items), default=0) + 1
        line = CreditNoteLineItem(
            credit_note=note, line_number=line_number, description=description.strip(), quantity=quantity,
            unit_amount=unit_amount, subtotal=subtotal, tax=tax, total=total, created_at=self._now(),
        )
        try:
            self.session.add(line)
            self._recalculate(note)
            self._touch(note)
            self.session.flush()
        except SQLAlchemyError as exc:
            raise BillingPersistenceConflictError("Unable to persist credit note line item.") from exc
        return line

    def remove_line_item(self, credit_note_id, line_item_id) -> CreditNote:
        note = self._draft(credit_note_id); self._id(line_item_id, "line_item_id")
        line = next((item for item in note.line_items if item.id == line_item_id), None)
        if line is None: self._invalid("Credit note line item was not found.")
        try:
            self.session.delete(line)
            # Exclude the object immediately because relationship collections are
            # not guaranteed to refresh until after the next flush.
            self._recalculate(note, exclude=line)
            self._touch(note)
            self.session.flush()
            self.session.expire(note, ["line_items"])
        except SQLAlchemyError as exc:
            raise BillingPersistenceConflictError("Unable to remove credit note line item.") from exc
        return note

    def issue_credit_note(self, credit_note_id) -> CreditNote:
        note = self._draft(credit_note_id)
        if not note.line_items: self._invalid("Credit note requires at least one line item.")
        invoice = self._invoice(note.invoice_id)
        if invoice.organization_id != note.organization_id: self._invalid("Invoice does not belong to credit note organization.")
        if invoice.currency != note.currency: self._invalid("Credit note currency does not match invoice currency.")
        if invoice.status not in {"open", "paid"}: self._invalid("Invoice cannot receive a credit in its current state.")
        self._recalculate(note)
        if note.total <= _ZERO: self._invalid("Credit note total must be positive before issuance.")
        now = self._now()
        note.status = "issued"; note.issued_at = now; note.voided_at = None
        self._touch(note, now)
        try: self.session.flush()
        except SQLAlchemyError as exc: raise BillingPersistenceConflictError("Unable to issue credit note.") from exc
        return note

    def void_credit_note(self, credit_note_id) -> CreditNote:
        note = self._note(credit_note_id)
        if note.status != "issued": self._invalid("Only issued credit notes may be voided.")
        if self._money(note.amount_applied) != _ZERO or self._money(note.amount_remaining) != self._money(note.total):
            self._invalid("Applied credit notes cannot be voided.")
        now = self._now()
        note.status = "void"; note.voided_at = now
        self._touch(note, now)
        try: self.session.flush()
        except SQLAlchemyError as exc: raise BillingPersistenceConflictError("Unable to void credit note.") from exc
        return note

    def _draft(self, credit_note_id) -> CreditNote:
        note = self._note(credit_note_id)
        if note.status != "draft": self._invalid("Only draft credit notes may be modified.")
        return note

    def _note(self, credit_note_id) -> CreditNote:
        self._id(credit_note_id, "credit_note_id")
        try: note = self.credit_notes.get_by_id(credit_note_id)
        except SQLAlchemyError as exc: raise BillingPersistenceConflictError("Unable to load credit note.") from exc
        if note is None: self._invalid("Credit note was not found.")
        return note

    def _invoice(self, invoice_id):
        try: invoice = self.invoices.get_by_id(invoice_id)
        except SQLAlchemyError as exc: raise BillingPersistenceConflictError("Unable to load invoice.") from exc
        if invoice is None: raise InvoiceNotFoundError("Invoice was not found.")
        return invoice

    def _recalculate(self, note: CreditNote, *, exclude=None) -> None:
        lines = (line for line in note.line_items if line is not exclude)
        subtotal = tax = total = _ZERO
        for line in lines:
            subtotal = self._money(subtotal + self._nonnegative_decimal(line.subtotal, "line subtotal"))
            tax = self._money(tax + self._nonnegative_decimal(line.tax, "line tax"))
            total = self._money(total + self._nonnegative_decimal(line.total, "line total"))
        note.subtotal = subtotal; note.tax = tax; note.total = total
        note.amount_applied = _ZERO; note.amount_remaining = total

    def _touch(self, note: CreditNote, now=None) -> None:
        note.version += 1; note.updated_at = now or self._now()

    @staticmethod
    def _id(value, name):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0: CreditNoteService._invalid(f"{name} must be a positive integer.")

    @staticmethod
    def _nonblank(value, name):
        if not isinstance(value, str) or not value.strip(): CreditNoteService._invalid(f"{name} must be non-blank.")

    @staticmethod
    def _currency(value):
        if not isinstance(value, str) or len(value) != 3 or not value.isupper(): CreditNoteService._invalid("currency must be an uppercase three-letter code.")

    @staticmethod
    def _invalid(message): raise BillingError(message)

    @staticmethod
    def _money(value) -> Decimal:
        if isinstance(value, float): CreditNoteService._invalid("Money values must not be floats.")
        try: return Decimal(value).quantize(_QUANTUM, rounding=ROUND_HALF_UP)
        except (InvalidOperation, TypeError, ValueError) as exc: raise BillingError("Invalid Decimal value.") from exc

    @classmethod
    def _nonnegative_decimal(cls, value, name) -> Decimal:
        result = cls._money(value)
        if result < _ZERO: cls._invalid(f"{name} must be non-negative.")
        return result

    @classmethod
    def _positive_decimal(cls, value, name) -> Decimal:
        result = cls._money(value)
        if result <= _ZERO: cls._invalid(f"{name} must be positive.")
        return result

    def _now(self):
        now = self.clock()
        if not isinstance(now, datetime) or now.tzinfo is None: self._invalid("Clock must return a timezone-aware datetime.")
        return now.astimezone(timezone.utc)
