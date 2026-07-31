from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, event, insert, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import configure_mappers, sessionmaker

from app.commercial.models import BillingAccount, CreditNote, CreditNoteLineItem, Invoice, Plan, Subscription
from app.db.database import Base
from app.db.organization_table import organization_table
from app.db.user_table import user_table


NOW = datetime(2026, 7, 29, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    event.listen(engine, "connect", lambda connection, _: connection.execute("PRAGMA foreign_keys=ON"))
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine, expire_on_commit=False)()
    db.execute(insert(user_table), [{"id": 1, "email": "credit1@test", "password_hash": "x"}, {"id": 2, "email": "credit2@test", "password_hash": "x"}])
    db.execute(insert(organization_table), [
        {"id": 1, "name": "One", "slug": "credit-one", "owner_user_id": 1, "plan": "free", "subscription_status": "inactive", "is_active": True},
        {"id": 2, "name": "Two", "slug": "credit-two", "owner_user_id": 2, "plan": "free", "subscription_status": "inactive", "is_active": True},
    ])
    db.add_all([Plan(id=1, code="credit", name="Credit", seat_limit=1), BillingAccount(id=1, organization_id=1, billing_email="one@test", billing_name="One", country_code="CA", currency="CAD"), BillingAccount(id=2, organization_id=2, billing_email="two@test", billing_name="Two", country_code="CA", currency="CAD")])
    db.add_all([Subscription(id=1, organization_id=1, plan_id=1, status="active", billing_cycle="monthly", starts_at=NOW), Subscription(id=2, organization_id=2, plan_id=1, status="active", billing_cycle="monthly", starts_at=NOW)])
    db.flush()
    db.add_all([make_invoice(1, 1), make_invoice(2, 2)])
    db.commit()
    try:
        yield db
    finally:
        db.close(); engine.dispose()


def make_invoice(identifier, organization_id):
    return Invoice(id=identifier, organization_id=organization_id, billing_account_id=organization_id, subscription_id=organization_id, invoice_number=f"INV-{identifier}", status="open", currency="CAD", period_start=NOW, period_end=datetime(2026, 8, 1, tzinfo=timezone.utc), subtotal_amount=Decimal("10"), tax_amount=Decimal("0"), discount_amount=Decimal("0"), total_amount=Decimal("10"), amount_due=Decimal("10"), amount_paid=Decimal("0"))


def make_credit(**overrides):
    values = dict(organization_id=1, invoice_id=1, credit_note_number="CN-1", status="draft", currency="CAD", subtotal=Decimal("10.0000"), tax=Decimal("0.0000"), total=Decimal("10.0000"), amount_applied=Decimal("0.0000"), amount_remaining=Decimal("10.0000"), created_at=NOW, updated_at=NOW)
    values.update(overrides)
    return CreditNote(**values)


def test_credit_note_schema_and_required_columns(session):
    columns = {column["name"]: column for column in inspect(session.bind).get_columns("credit_notes")}
    assert set(("id", "organization_id", "invoice_id", "credit_note_number", "status", "currency", "reason", "subtotal", "tax", "total", "amount_applied", "amount_remaining", "issued_at", "voided_at", "created_at", "updated_at", "version")) <= columns.keys()
    assert all(not columns[name]["nullable"] for name in ("organization_id", "invoice_id", "credit_note_number", "status", "currency"))


def test_defaults_relationships_decimal_round_trip_and_timestamps(session):
    credit = make_credit(credit_note_number="CN-DEFAULT", subtotal=Decimal("1.2345"), total=Decimal("1.2345"), amount_remaining=Decimal("1.2345"), amount_applied=None)
    # Let SQLAlchemy apply the mapped default rather than passing a nullable value.
    del credit.__dict__["amount_applied"]
    session.add(credit); session.commit(); session.expire_all()
    stored = session.get(CreditNote, credit.id)
    assert stored.amount_applied == Decimal("0.0000") and stored.version == 1
    assert stored.issued_at is None and stored.voided_at is None
    assert stored.subtotal == Decimal("1.2345") and stored.created_at is not None and stored.updated_at is not None
    assert stored.organization.id == 1 and stored.invoice.id == 1


def test_organization_scoped_number_is_unique_but_reusable_across_organizations(session):
    session.add(make_credit(credit_note_number="CN-SAME")); session.flush()
    session.add(make_credit(credit_note_number="CN-SAME"))
    with pytest.raises(IntegrityError): session.flush()
    session.rollback()
    session.add(make_credit(organization_id=2, invoice_id=2, credit_note_number="CN-SAME")); session.commit()
    assert session.query(CreditNote).count() == 1


@pytest.mark.parametrize("field", ["subtotal", "tax", "total", "amount_applied", "amount_remaining"])
def test_negative_monetary_values_are_rejected(session, field):
    values = {field: Decimal("-0.0001")}
    if field == "total": values["amount_remaining"] = Decimal("0")
    session.add(make_credit(**values))
    with pytest.raises(IntegrityError): session.flush()


@pytest.mark.parametrize("applied,remaining", [("10.0001", "0"), ("0", "10.0001"), ("6", "5")])
def test_invalid_credit_balances_are_rejected(session, applied, remaining):
    session.add(make_credit(amount_applied=Decimal(applied), amount_remaining=Decimal(remaining)))
    with pytest.raises(IntegrityError): session.flush()


def test_line_items_are_ordered_related_and_use_decimal_money(session):
    credit = make_credit(); session.add(credit); session.flush()
    second = CreditNoteLineItem(credit_note_id=credit.id, line_number=2, description="Second", quantity=Decimal("1"), unit_amount=Decimal("2.0000"), subtotal=Decimal("2.0000"), tax=Decimal("0"), total=Decimal("2.0000"), created_at=NOW)
    first = CreditNoteLineItem(credit_note_id=credit.id, line_number=1, description="First", quantity=Decimal("1"), unit_amount=Decimal("1.2345"), subtotal=Decimal("1.2345"), tax=Decimal("0"), total=Decimal("1.2345"), created_at=NOW)
    session.add_all([second, first]); session.commit(); session.expire_all()
    stored = session.get(CreditNote, credit.id)
    assert [item.line_number for item in stored.line_items] == [1, 2]
    assert stored.line_items[0].credit_note is stored and stored.line_items[0].unit_amount == Decimal("1.2345")


def test_line_item_foreign_key_and_restrictive_parent_delete(session):
    credit = make_credit(); session.add(credit); session.flush()
    session.add(CreditNoteLineItem(credit_note_id=credit.id, line_number=1, description="Item", quantity=Decimal("1"), unit_amount=Decimal("1"), subtotal=Decimal("1"), tax=Decimal("0"), total=Decimal("1"), created_at=NOW)); session.commit()
    session.delete(credit)
    with pytest.raises(IntegrityError): session.flush()


def test_caller_rollback_and_commit_control_persistence(session):
    credit = make_credit(); session.add(credit); session.flush(); session.rollback()
    assert session.get(CreditNote, credit.id) is None
    credit = make_credit(credit_note_number="CN-COMMIT"); session.add(credit); session.commit()
    assert session.get(CreditNote, credit.id) is not None


def test_mapper_configuration_and_no_duplicate_registration(session):
    configure_mappers()
    assert CreditNote.__table__.name == "credit_notes"
    assert CreditNoteLineItem.__table__.name == "credit_note_line_items"
    assert list(Base.metadata.tables).count("credit_notes") == 1
