from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, event, insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import configure_mappers, sessionmaker

from app.commercial.billing import BillingError, BillingPersistenceConflictError
from app.commercial.credit_note_service import CreditNoteService
from app.commercial.invoice_service import InvoiceNotFoundError
from app.commercial.models import BillingAccount, CreditNote, CreditNoteLineItem, Invoice, Plan, Subscription
from app.commercial.repositories import SqlAlchemyCreditNoteRepository, SqlAlchemyInvoiceRepository
from app.db.database import Base
from app.db.organization_table import organization_table
from app.db.user_table import user_table


NOW = datetime(2026, 7, 29, 14, 0, tzinfo=timezone.utc)


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    event.listen(engine, "connect", lambda connection, _: connection.execute("PRAGMA foreign_keys=ON"))
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine, expire_on_commit=False)()
    db.execute(insert(user_table), [{"id": 1, "email": "service1@test", "password_hash": "x"}, {"id": 2, "email": "service2@test", "password_hash": "x"}])
    db.execute(insert(organization_table), [
        {"id": 1, "name": "One", "slug": "service-one", "owner_user_id": 1, "plan": "free", "subscription_status": "inactive", "is_active": True},
        {"id": 2, "name": "Two", "slug": "service-two", "owner_user_id": 2, "plan": "free", "subscription_status": "inactive", "is_active": True},
    ])
    db.add(Plan(id=1, code="credit-service", name="Credit service", seat_limit=1))
    db.add_all([BillingAccount(id=1, organization_id=1, billing_email="one@test", billing_name="One", country_code="CA", currency="CAD"), BillingAccount(id=2, organization_id=2, billing_email="two@test", billing_name="Two", country_code="CA", currency="CAD")])
    db.add_all([Subscription(id=1, organization_id=1, plan_id=1, status="active", billing_cycle="monthly", starts_at=NOW), Subscription(id=2, organization_id=2, plan_id=1, status="active", billing_cycle="monthly", starts_at=NOW)])
    db.flush(); db.add_all([make_invoice(1, 1), make_invoice(2, 2)]); db.commit()
    try: yield db
    finally: db.close(); engine.dispose()


def make_invoice(identifier, organization_id, *, currency="CAD", status="open"):
    account = subscription = organization_id
    return Invoice(id=identifier, organization_id=organization_id, billing_account_id=account, subscription_id=subscription, invoice_number=f"INV-S-{identifier}", status=status, currency=currency, period_start=NOW, period_end=NOW + timedelta(days=31), subtotal_amount=Decimal("10"), tax_amount=Decimal("0"), discount_amount=Decimal("0"), total_amount=Decimal("10"), amount_due=Decimal("10"), amount_paid=Decimal("0"))


def service(session):
    return CreditNoteService(session, credit_note_repository=SqlAlchemyCreditNoteRepository(session), invoice_repository=SqlAlchemyInvoiceRepository(session), clock=lambda: NOW)


def draft(session, number="CN-S-1"):
    return service(session).create_draft(organization_id=1, invoice_id=1, credit_note_number=number, currency="CAD", reason="Adjustment")


def test_create_draft_initializes_canonical_state_and_timestamps(session):
    note = draft(session)
    assert (note.organization_id, note.invoice_id, note.credit_note_number, note.currency, note.reason, note.status) == (1, 1, "CN-S-1", "CAD", "Adjustment", "draft")
    assert (note.subtotal, note.tax, note.total, note.amount_applied, note.amount_remaining) == (Decimal("0.0000"),) * 5
    assert note.issued_at is None and note.voided_at is None and note.version == 1
    assert note.created_at == NOW and note.updated_at == NOW


def test_create_draft_validates_invoice_ownership_currency_number_and_conflicts(session):
    with pytest.raises(InvoiceNotFoundError): service(session).create_draft(organization_id=1, invoice_id=99, credit_note_number="CN-MISSING", currency="CAD")
    with pytest.raises(BillingError): service(session).create_draft(organization_id=2, invoice_id=1, credit_note_number="CN-ORG", currency="CAD")
    with pytest.raises(BillingError): service(session).create_draft(organization_id=1, invoice_id=1, credit_note_number="CN-CURRENCY", currency="USD")
    with pytest.raises(BillingError): service(session).create_draft(organization_id=1, invoice_id=1, credit_note_number=" ", currency="CAD")
    draft(session, "CN-DUP"); session.commit()
    with pytest.raises(BillingPersistenceConflictError): draft(session, "CN-DUP")
    session.rollback()


def test_add_line_item_calculates_quantized_totals_and_updates_version(session):
    note = draft(session); version = note.version
    line = service(session).add_line_item(note.id, description="Service credit", quantity=Decimal("2.0000"), unit_amount=Decimal("1.23456"), tax=Decimal("0.11115"))
    assert (line.quantity, line.unit_amount, line.subtotal, line.tax, line.total) == (Decimal("2.0000"), Decimal("1.2346"), Decimal("2.4692"), Decimal("0.1112"), Decimal("2.5804"))
    assert (note.subtotal, note.tax, note.total, note.amount_applied, note.amount_remaining) == (Decimal("2.4692"), Decimal("0.1112"), Decimal("2.5804"), Decimal("0.0000"), Decimal("2.5804"))
    assert note.version == version + 1 and note.updated_at == NOW and line.credit_note is note


@pytest.mark.parametrize("kwargs", [
    {"description": "x", "quantity": 0, "unit_amount": Decimal("1")},
    {"description": "x", "quantity": Decimal("-1"), "unit_amount": Decimal("1")},
    {"description": "x", "quantity": Decimal("1"), "unit_amount": Decimal("-1")},
    {"description": "x", "quantity": Decimal("1"), "unit_amount": Decimal("1"), "tax": Decimal("-1")},
    {"description": " ", "quantity": Decimal("1"), "unit_amount": Decimal("1")},
    {"description": "x", "quantity": 1.0, "unit_amount": Decimal("1")},
])
def test_add_line_item_rejects_invalid_values_without_mutating_draft(session, kwargs):
    note = draft(session); snapshot = (note.version, note.updated_at, note.total, len(note.line_items))
    with pytest.raises(BillingError): service(session).add_line_item(note.id, **kwargs)
    assert (note.version, note.updated_at, note.total, len(note.line_items)) == snapshot


@pytest.mark.parametrize("status", ["issued", "fully_applied", "void"])
def test_add_line_item_rejects_non_draft_credit_notes(session, status):
    note = draft(session); note.status = status; session.flush()
    with pytest.raises(BillingError): service(session).add_line_item(note.id, description="x", quantity=Decimal("1"), unit_amount=Decimal("1"))


def test_remove_line_item_recalculates_draft_and_rejects_foreign_line(session):
    note = draft(session); first = service(session).add_line_item(note.id, description="first", quantity=Decimal("1"), unit_amount=Decimal("2")); second = service(session).add_line_item(note.id, description="second", quantity=Decimal("1"), unit_amount=Decimal("3")); version = note.version
    updated = service(session).remove_line_item(note.id, first.id)
    assert updated is note and [item.id for item in note.line_items] == [second.id]
    assert (note.subtotal, note.total, note.amount_remaining, note.version) == (Decimal("3.0000"), Decimal("3.0000"), Decimal("3.0000"), version + 1)
    other = draft(session, "CN-OTHER"); other_line = service(session).add_line_item(other.id, description="other", quantity=Decimal("1"), unit_amount=Decimal("1"))
    with pytest.raises(BillingError): service(session).remove_line_item(note.id, other_line.id)


@pytest.mark.parametrize("status", ["issued", "void"])
def test_remove_line_item_from_non_draft_is_rejected(session, status):
    note = draft(session); line = service(session).add_line_item(note.id, description="line", quantity=Decimal("1"), unit_amount=Decimal("1")); note.status = status; session.flush()
    with pytest.raises(BillingError): service(session).remove_line_item(note.id, line.id)


def test_issue_credit_note_preserves_invoice_and_lines_and_void_lifecycle(session):
    note = draft(session); line = service(session).add_line_item(note.id, description="line", quantity=Decimal("1"), unit_amount=Decimal("4")); version = note.version
    issued = service(session).issue_credit_note(note.id)
    assert issued.status == "issued" and issued.issued_at == NOW and issued.voided_at is None
    assert (issued.total, issued.amount_applied, issued.amount_remaining, issued.version) == (Decimal("4.0000"), Decimal("0.0000"), Decimal("4.0000"), version + 1)
    assert issued.line_items == [line] and session.get(Invoice, 1).amount_due == Decimal("10.0000")
    version = issued.version; voided = service(session).void_credit_note(issued.id)
    assert voided.status == "void" and voided.voided_at == NOW and voided.issued_at == NOW and voided.version == version + 1
    assert (voided.total, voided.amount_remaining, voided.line_items) == (Decimal("4.0000"), Decimal("4.0000"), [line])


def test_issue_rejects_empty_zero_invalid_status_and_invoice_conditions(session):
    empty = draft(session)
    with pytest.raises(BillingError): service(session).issue_credit_note(empty.id)
    zero = draft(session, "CN-ZERO"); service(session).add_line_item(zero.id, description="zero", quantity=Decimal("1"), unit_amount=Decimal("0"))
    with pytest.raises(BillingError): service(session).issue_credit_note(zero.id)
    note = draft(session, "CN-STATUS"); service(session).add_line_item(note.id, description="line", quantity=Decimal("1"), unit_amount=Decimal("1")); note.status = "void"; session.flush()
    with pytest.raises(BillingError): service(session).issue_credit_note(note.id)
    broken = draft(session, "CN-BROKEN"); service(session).add_line_item(broken.id, description="line", quantity=Decimal("1"), unit_amount=Decimal("1")); session.get(Invoice, 1).status = "draft"; session.flush()
    with pytest.raises(BillingError): service(session).issue_credit_note(broken.id)


@pytest.mark.parametrize("status,applied,remaining", [("draft", "0", "0"), ("fully_applied", "1", "0"), ("void", "0", "1"), ("issued", "0.5", "0.5"), ("issued", "1", "0")])
def test_void_rejects_ineligible_lifecycle_states(session, status, applied, remaining):
    note = draft(session); note.status = status; note.total = Decimal("1"); note.amount_applied = Decimal(applied); note.amount_remaining = Decimal(remaining); session.flush()
    with pytest.raises(BillingError): service(session).void_credit_note(note.id)


def test_caller_commit_and_rollback_reverse_all_service_mutations(session):
    note = draft(session, "CN-ROLLBACK"); session.rollback(); assert session.query(CreditNote).filter_by(credit_note_number="CN-ROLLBACK").first() is None
    note = draft(session, "CN-TRANSACTION"); service(session).add_line_item(note.id, description="line", quantity=Decimal("1"), unit_amount=Decimal("2")); session.commit(); note_id = note.id
    service(session).issue_credit_note(note_id); session.rollback(); session.expire_all(); assert session.get(CreditNote, note_id).status == "draft"
    service(session).remove_line_item(note_id, session.get(CreditNote, note_id).line_items[0].id); session.rollback(); session.expire_all(); assert len(session.get(CreditNote, note_id).line_items) == 1
    service(session).issue_credit_note(note_id); session.commit(); service(session).void_credit_note(note_id); session.rollback(); session.expire_all(); assert session.get(CreditNote, note_id).status == "issued"


def test_service_never_commits_or_rolls_back_and_mapper_is_clean(session, monkeypatch):
    note = draft(session, "CN-NO-COMMIT")
    monkeypatch.setattr(session, "commit", lambda: pytest.fail("service committed")); monkeypatch.setattr(session, "rollback", lambda: pytest.fail("service rolled back"))
    service(session).add_line_item(note.id, description="line", quantity=Decimal("1"), unit_amount=Decimal("1"))
    configure_mappers(); assert list(Base.metadata.tables).count("credit_notes") == 1


def test_raw_sqlalchemy_errors_are_mapped(session, monkeypatch):
    class BrokenRepository:
        def get_by_id(self, _): raise SQLAlchemyError("broken")
    with pytest.raises(BillingPersistenceConflictError): CreditNoteService(session, credit_note_repository=BrokenRepository(), clock=lambda: NOW).issue_credit_note(1)
