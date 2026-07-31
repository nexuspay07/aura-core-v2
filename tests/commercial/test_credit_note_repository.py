from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, event, insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import configure_mappers, sessionmaker

from app.commercial.billing import BillingError, BillingPersistenceConflictError
from app.commercial.models import BillingAccount, CreditNote, CreditNoteLineItem, Invoice, Plan, Subscription
from app.commercial.repositories import SqlAlchemyCreditNoteRepository
from app.db.database import Base
from app.db.organization_table import organization_table
from app.db.user_table import user_table


NOW = datetime(2026, 7, 29, 13, 0, tzinfo=timezone.utc)


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    event.listen(engine, "connect", lambda connection, _: connection.execute("PRAGMA foreign_keys=ON"))
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine, expire_on_commit=False)()
    db.execute(insert(user_table), [{"id": 1, "email": "repo1@test", "password_hash": "x"}, {"id": 2, "email": "repo2@test", "password_hash": "x"}])
    db.execute(insert(organization_table), [
        {"id": 1, "name": "One", "slug": "repo-one", "owner_user_id": 1, "plan": "free", "subscription_status": "inactive", "is_active": True},
        {"id": 2, "name": "Two", "slug": "repo-two", "owner_user_id": 2, "plan": "free", "subscription_status": "inactive", "is_active": True},
    ])
    db.add(Plan(id=1, code="repo-credit", name="Repo credit", seat_limit=1))
    db.add_all([BillingAccount(id=1, organization_id=1, billing_email="one@test", billing_name="One", country_code="CA", currency="CAD"), BillingAccount(id=2, organization_id=2, billing_email="two@test", billing_name="Two", country_code="CA", currency="CAD")])
    db.add_all([Subscription(id=1, organization_id=1, plan_id=1, status="active", billing_cycle="monthly", starts_at=NOW), Subscription(id=2, organization_id=2, plan_id=1, status="active", billing_cycle="monthly", starts_at=NOW)])
    db.flush(); db.add_all([invoice(1, 1), invoice(2, 1), invoice(3, 2)]); db.commit()
    try: yield db
    finally: db.close(); engine.dispose()


def invoice(identifier, organization_id):
    return Invoice(id=identifier, organization_id=organization_id, billing_account_id=1 if organization_id == 1 else 2, subscription_id=1 if organization_id == 1 else 2, invoice_number=f"INV-R-{identifier}", status="open", currency="CAD", period_start=NOW, period_end=NOW + timedelta(days=31), subtotal_amount=Decimal("10"), tax_amount=Decimal("0"), discount_amount=Decimal("0"), total_amount=Decimal("10"), amount_due=Decimal("10"), amount_paid=Decimal("0"))


def credit(number="CN-1", *, organization_id=1, invoice_id=1, created_at=NOW):
    return CreditNote(organization_id=organization_id, invoice_id=invoice_id, credit_note_number=number, status="draft", currency="CAD", subtotal=Decimal("2.1250"), tax=Decimal("0.3750"), total=Decimal("2.5000"), amount_applied=Decimal("0"), amount_remaining=Decimal("2.5000"), created_at=created_at, updated_at=created_at)


def repository(session): return SqlAlchemyCreditNoteRepository(session)


def test_save_returns_and_preserves_credit_note_aggregate(session):
    note = credit(); note.line_items.append(CreditNoteLineItem(line_number=1, description="Credit", quantity=Decimal("1"), unit_amount=Decimal("2.5000"), subtotal=Decimal("2.1250"), tax=Decimal("0.3750"), total=Decimal("2.5000"), created_at=NOW))
    saved = repository(session).save(note)
    assert saved is note and note.id is not None
    assert (note.organization_id, note.invoice_id, note.credit_note_number, note.status, note.subtotal, note.tax, note.total) == (1, 1, "CN-1", "draft", Decimal("2.1250"), Decimal("0.3750"), Decimal("2.5000"))
    assert note.line_items[0].credit_note is note


def test_get_by_id_and_scoped_number(session):
    note = repository(session).save(credit("CN-SCOPED")); session.commit()
    assert repository(session).get_by_id(note.id) is note
    assert repository(session).get_by_id(999) is None
    assert repository(session).get_by_organization_and_number(1, "CN-SCOPED") is note
    assert repository(session).get_by_organization_and_number(2, "CN-SCOPED") is None


def test_lists_filter_order_and_paginate_deterministically(session):
    repo = repository(session)
    first = repo.save(credit("CN-FIRST", created_at=NOW))
    second = repo.save(credit("CN-SECOND", created_at=NOW))
    other_invoice = repo.save(credit("CN-OTHER", invoice_id=2, created_at=NOW + timedelta(seconds=1)))
    other_org = repo.save(credit("CN-ORG-2", organization_id=2, invoice_id=3, created_at=NOW + timedelta(seconds=2)))
    assert [note.id for note in repo.list_by_invoice(1)] == [second.id, first.id]
    assert repo.list_by_invoice(999) == []
    assert [note.id for note in repo.list_by_organization(1)] == [other_invoice.id, second.id, first.id]
    assert repo.list_by_organization(999) == []
    assert [note.id for note in repo.list_by_organization(1, limit=1, offset=1)] == [second.id]
    assert repo.list_by_organization(2) == [other_org]


def test_duplicate_and_foreign_key_conflicts_are_mapped_and_caller_can_rollback(session):
    repo = repository(session); repo.save(credit("CN-DUP")); session.commit()
    with pytest.raises(BillingPersistenceConflictError): repo.save(credit("CN-DUP"))
    session.rollback()
    assert repo.get_by_organization_and_number(1, "CN-DUP") is not None
    with pytest.raises(BillingPersistenceConflictError): repo.save(credit("CN-FK", invoice_id=999))
    session.rollback()


@pytest.mark.parametrize("method,args", [("get_by_id", (None,)), ("get_by_id", (0,)), ("get_by_organization_and_number", (0, "CN")), ("get_by_organization_and_number", (1, " ")), ("list_by_invoice", (0,)), ("list_by_organization", (None,))])
def test_invalid_lookup_inputs_are_rejected(session, method, args):
    with pytest.raises(BillingError): getattr(repository(session), method)(*args)


@pytest.mark.parametrize("kwargs", [{"limit": 0}, {"limit": "1"}, {"offset": -1}, {"offset": True}])
def test_invalid_pagination_is_rejected(session, kwargs):
    with pytest.raises(BillingError): repository(session).list_by_invoice(1, **kwargs)


def test_wrong_save_type_and_raw_sqlalchemy_query_error_are_mapped(session, monkeypatch):
    repo = repository(session)
    with pytest.raises(BillingError): repo.save(object())
    monkeypatch.setattr(session, "get", lambda *_: (_ for _ in ()).throw(SQLAlchemyError("database unavailable")))
    with pytest.raises(BillingPersistenceConflictError): repo.get_by_id(1)


def test_repository_never_commits_or_rolls_back(session, monkeypatch):
    repo = repository(session); note = credit("CN-TX")
    monkeypatch.setattr(session, "commit", lambda: pytest.fail("repository committed"))
    monkeypatch.setattr(session, "rollback", lambda: pytest.fail("repository rolled back"))
    repo.save(note); repo.get_by_id(note.id); repo.list_by_invoice(1)
    assert session.in_transaction()


def test_caller_commit_and_rollback_control_save(session):
    repo = repository(session); rolled_back = repo.save(credit("CN-ROLLBACK")); session.rollback()
    assert repo.get_by_id(rolled_back.id) is None
    committed = repo.save(credit("CN-COMMIT")); session.commit(); session.expire_all()
    assert repo.get_by_id(committed.id).credit_note_number == "CN-COMMIT"


def test_session_remains_usable_mapper_and_metadata_are_canonical(session):
    configure_mappers(); repo = repository(session)
    repo.save(credit("CN-USABLE")); assert repo.list_by_invoice(1)
    assert list(Base.metadata.tables).count("credit_notes") == 1
