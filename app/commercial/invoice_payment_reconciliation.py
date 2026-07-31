"""Provider-neutral, durable application of succeeded payment attempts to invoices."""

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from sqlalchemy import update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.commercial.billing import BillingPersistenceConflictError
from app.commercial.invoice_service import (
    InvoiceInputError,
    InvoiceNotFoundError,
    InvoiceTransitionError,
)
from app.commercial.models import Invoice, PaymentAttempt
from app.commercial.payment_attempt_service import (
    PaymentAttemptError,
    PaymentAttemptTransitionError,
)
from app.commercial.repositories import (
    InvoiceRepository,
    PaymentAttemptRepository,
    SqlAlchemyInvoiceRepository,
    SqlAlchemyPaymentAttemptRepository,
)


_MONEY_QUANTUM = Decimal("0.0001")


class InvoicePaymentReconciliationService:
    """Apply a succeeded payment attempt exactly once within the caller's transaction.

    A replay of an attempt whose ``reconciled_at`` marker is already set is successful:
    the associated invoice is returned without changing either aggregate.  The marker is
    claimed with a conditional database update, so two concurrent callers cannot apply
    the same attempt twice.
    """

    def __init__(
        self,
        session: Session,
        *,
        invoice_repository: InvoiceRepository | None = None,
        payment_attempt_repository: PaymentAttemptRepository | None = None,
        clock=lambda: datetime.now(timezone.utc),
    ):
        self.session = session
        self.invoices = invoice_repository or SqlAlchemyInvoiceRepository(session)
        self.payment_attempts = payment_attempt_repository or SqlAlchemyPaymentAttemptRepository(session)
        self.clock = clock

    def reconcile_succeeded_attempt(self, payment_attempt_id: int) -> Invoice:
        if isinstance(payment_attempt_id, bool) or not isinstance(payment_attempt_id, int) or payment_attempt_id <= 0:
            raise InvoiceInputError("payment_attempt_id must be a positive integer.")

        attempt = self.payment_attempts.get_by_id(payment_attempt_id)
        if attempt is None:
            raise PaymentAttemptError("Payment attempt was not found.")

        invoice = self.invoices.get_by_id(attempt.invoice_id)
        if invoice is None:
            raise InvoiceNotFoundError("Invoice for payment attempt was not found.")

        # An already-claimed attempt is a successful no-op, even if the invoice has
        # subsequently transitioned to paid.
        if attempt.reconciled_at is not None:
            return invoice

        if attempt.status != "succeeded":
            raise PaymentAttemptTransitionError("Only succeeded payment attempts can be reconciled.")
        if invoice.status != "open":
            raise InvoiceTransitionError("Invoice cannot accept a payment in its current state.")
        if attempt.currency != invoice.currency:
            raise InvoiceInputError("Payment attempt currency does not match the invoice currency.")

        amount = self._positive_decimal(attempt.amount)
        current_paid = self._decimal(invoice.amount_paid)
        current_due = self._decimal(invoice.amount_due)
        total = self._decimal(invoice.total_amount)
        if amount > current_due:
            raise InvoiceTransitionError("Payment amount exceeds the remaining invoice balance.")

        new_paid = self._quantize(current_paid + amount)
        new_due = self._quantize(total - new_paid)
        if new_due < Decimal("0"):
            raise InvoiceTransitionError("Payment would make the invoice balance negative.")

        now = self._utc_now()
        try:
            claim = self.session.execute(
                update(PaymentAttempt)
                .where(
                    PaymentAttempt.id == payment_attempt_id,
                    PaymentAttempt.reconciled_at.is_(None),
                    PaymentAttempt.status == "succeeded",
                )
                .values(
                    reconciled_at=now,
                    updated_at=now,
                    version=PaymentAttempt.version + 1,
                )
            )
        except SQLAlchemyError as exc:
            raise BillingPersistenceConflictError("Unable to claim payment attempt for reconciliation.") from exc

        if claim.rowcount != 1:
            self.session.expire(attempt)
            current = self.payment_attempts.get_by_id(payment_attempt_id)
            if current is not None and current.reconciled_at is not None:
                replay_invoice = self.invoices.get_by_id(current.invoice_id)
                if replay_invoice is None:
                    raise InvoiceNotFoundError("Invoice for payment attempt was not found.")
                return replay_invoice
            raise PaymentAttemptTransitionError("Payment attempt reconciliation claim failed.")

        try:
            invoice.amount_paid = new_paid
            invoice.amount_due = new_due
            invoice.updated_at = now
            invoice.version += 1
            if new_due == Decimal("0.0000"):
                invoice.status = "paid"
                invoice.paid_at = now
            self.session.flush()
            self.session.expire(attempt)
        except (InvalidOperation, SQLAlchemyError) as exc:
            raise BillingPersistenceConflictError("Unable to persist invoice payment reconciliation.") from exc
        return invoice

    @staticmethod
    def _decimal(value) -> Decimal:
        try:
            return Decimal(value)
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise InvoiceInputError("Invoice monetary values must be Decimal-compatible.") from exc

    def _positive_decimal(self, value) -> Decimal:
        if not isinstance(value, Decimal):
            raise InvoiceInputError("Payment amount must be a Decimal.")
        amount = self._quantize(value)
        if amount <= Decimal("0"):
            raise InvoiceInputError("Payment amount must be positive.")
        return amount

    @staticmethod
    def _quantize(value: Decimal) -> Decimal:
        try:
            return Decimal(value).quantize(_MONEY_QUANTUM, rounding=ROUND_HALF_UP)
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise InvoiceInputError("Invalid monetary value.") from exc

    def _utc_now(self) -> datetime:
        now = self.clock()
        if not isinstance(now, datetime) or now.tzinfo is None:
            raise InvoiceInputError("Clock must return a timezone-aware datetime.")
        return now.astimezone(timezone.utc)
