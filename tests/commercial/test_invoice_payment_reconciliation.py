from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, event, insert, select
from sqlalchemy.orm import configure_mappers, sessionmaker

from app.commercial.invoice_payment_reconciliation import InvoicePaymentReconciliationService
from app.commercial.invoice_service import InvoiceInputError, InvoiceNotFoundError, InvoiceTransitionError
from app.commercial.models import BillingAccount, Invoice, PaymentAttempt, Plan, Subscription
from app.commercial.payment_attempt_service import PaymentAttemptError, PaymentAttemptTransitionError
from app.commercial.repositories import SqlAlchemyInvoiceRepository, SqlAlchemyPaymentAttemptRepository
from app.db.database import Base
from app.db.organization_table import organization_table
from app.db.user_table import user_table


NOW = datetime(2026, 7, 28, 15, 30, tzinfo=timezone.utc)
START = datetime(2026, 7, 1, tzinfo=timezone.utc)
END = datetime(2026, 8, 1, tzinfo=timezone.utc)


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    event.listen(engine, "connect", lambda connection, _: connection.execute("PRAGMA foreign_keys=ON"))
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    db = Session()
    db.execute(insert(user_table).values(id=1, email="reconcile@example.test", password_hash="x"))
    db.execute(insert(organization_table).values(
        id=1, name="Reconciliation", slug="reconciliation", owner_user_id=1,
        plan="free", subscription_status="inactive", is_active=True,
    ))
    db.add(Plan(id=1, code="reconciliation", name="Reconciliation", seat_limit=1))
    db.add(BillingAccount(id=1, organization_id=1, billing_email="billing@example.test", billing_name="Billing", country_code="CA", currency="CAD"))
    db.add(Subscription(id=1, organization_id=1, plan_id=1, status="active", billing_cycle="monthly", starts_at=START))
    db.commit()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


def make_invoice(session, *, invoice_id=1, total="10.0000", status="open", currency="CAD"):
    invoice = Invoice(
        id=invoice_id, organization_id=1, billing_account_id=1, subscription_id=1,
        invoice_number=f"INV-{invoice_id}", status=status, currency=currency,
        period_start=START, period_end=END, subtotal_amount=Decimal(total), tax_amount=Decimal("0"),
        discount_amount=Decimal("0"), total_amount=Decimal(total), amount_paid=Decimal("0"), amount_due=Decimal(total),
    )
    session.add(invoice)
    session.flush()
    return invoice


def make_attempt(session, invoice, *, attempt_id=1, amount="2.5000", status="succeeded", currency=None, reconciled_at=None):
    attempt = PaymentAttempt(
        id=attempt_id, invoice_id=invoice.id, attempt_number=attempt_id, provider="fake",
        provider_reference=f"reference-{attempt_id}", idempotency_key=f"key-{attempt_id}", status=status,
        amount=Decimal(amount), currency=currency or invoice.currency, requested_at=NOW,
        succeeded_at=NOW if status == "succeeded" else None, reconciled_at=reconciled_at,
    )
    session.add(attempt)
    session.flush()
    return attempt


def service(session):
    return InvoicePaymentReconciliationService(session, clock=lambda: NOW)


def test_succeeded_attempt_reconciles_and_preserves_attempt_fields(session):
    invoice = make_invoice(session)
    attempt = make_attempt(session, invoice)
    before = (attempt.status, attempt.amount, attempt.provider_reference, attempt.succeeded_at, attempt.version)
    result = service(session).reconcile_succeeded_attempt(attempt.id)
    assert result is invoice
    assert attempt.reconciled_at.replace(tzinfo=timezone.utc) == NOW
    assert (attempt.status, attempt.amount, attempt.provider_reference) == before[:3]
    assert attempt.succeeded_at.replace(tzinfo=timezone.utc) == before[3]
    assert attempt.version == before[4] + 1


def test_partial_payment_updates_quantized_balance_only(session):
    invoice = make_invoice(session, total="10.0000")
    make_attempt(session, invoice, amount="2.3333")
    service(session).reconcile_succeeded_attempt(1)
    assert invoice.amount_paid == Decimal("2.3333")
    assert invoice.amount_due == Decimal("7.6667")
    assert invoice.status == "open" and invoice.paid_at is None
    assert (invoice.subtotal_amount, invoice.tax_amount, invoice.discount_amount, invoice.total_amount) == (
        Decimal("10.0000"), Decimal("0"), Decimal("0"), Decimal("10.0000"),
    )


def test_full_payment_marks_invoice_paid_with_clock_and_one_version_increment(session):
    invoice = make_invoice(session, total="10.0000")
    make_attempt(session, invoice, amount="10.0000")
    version = invoice.version
    service(session).reconcile_succeeded_attempt(1)
    assert (invoice.amount_paid, invoice.amount_due, invoice.status, invoice.paid_at, invoice.updated_at) == (
        Decimal("10.0000"), Decimal("0.0000"), "paid", NOW, NOW,
    )
    assert invoice.version == version + 1


def test_replay_is_successful_noop_and_keeps_marker_and_versions(session):
    invoice = make_invoice(session)
    attempt = make_attempt(session, invoice)
    reconcile = service(session)
    reconcile.reconcile_succeeded_attempt(attempt.id)
    snapshot = (invoice.amount_paid, invoice.amount_due, invoice.status, invoice.paid_at, invoice.version, attempt.reconciled_at, attempt.version)
    assert reconcile.reconcile_succeeded_attempt(attempt.id) is invoice
    assert (invoice.amount_paid, invoice.amount_due, invoice.status, invoice.paid_at, invoice.version, attempt.reconciled_at, attempt.version) == snapshot


@pytest.mark.parametrize("attempt_id", [0, -1, True, "1", None])
def test_invalid_attempt_id_is_rejected(session, attempt_id):
    with pytest.raises(InvoiceInputError):
        service(session).reconcile_succeeded_attempt(attempt_id)


def test_missing_attempt_and_missing_invoice_are_rejected(session):
    with pytest.raises(PaymentAttemptError):
        service(session).reconcile_succeeded_attempt(99)
    invoice = make_invoice(session)
    attempt = make_attempt(session, invoice)
    class MissingInvoiceRepository:
        def get_by_id(self, _):
            return None

    with pytest.raises(InvoiceNotFoundError):
        InvoicePaymentReconciliationService(session, invoice_repository=MissingInvoiceRepository(), clock=lambda: NOW).reconcile_succeeded_attempt(attempt.id)


@pytest.mark.parametrize("status", ["pending", "processing", "failed", "cancelled"])
def test_non_succeeded_attempts_are_rejected(session, status):
    invoice = make_invoice(session)
    attempt = make_attempt(session, invoice, status=status)
    with pytest.raises(PaymentAttemptTransitionError):
        service(session).reconcile_succeeded_attempt(attempt.id)


@pytest.mark.parametrize("status", ["draft", "paid", "void", "uncollectible"])
def test_invoice_states_that_cannot_accept_payment_are_rejected(session, status):
    invoice = make_invoice(session, status=status)
    attempt = make_attempt(session, invoice)
    with pytest.raises(InvoiceTransitionError):
        service(session).reconcile_succeeded_attempt(attempt.id)


def test_currency_mismatch_and_overpayment_are_rejected(session):
    invoice = make_invoice(session)
    mismatch = make_attempt(session, invoice, currency="USD")
    with pytest.raises(InvoiceInputError):
        service(session).reconcile_succeeded_attempt(mismatch.id)
    overpayment = make_attempt(session, invoice, attempt_id=2, amount="10.0001")
    with pytest.raises(InvoiceTransitionError):
        service(session).reconcile_succeeded_attempt(overpayment.id)


@pytest.mark.parametrize("amount", [Decimal("0"), Decimal("-1")])
def test_non_positive_amount_is_rejected_before_claim(session, amount):
    invoice = make_invoice(session)
    attempt = make_attempt(session, invoice)
    # The database constraint correctly prevents such rows; directly assigning lets
    # the application boundary be tested without weakening the schema.
    attempt.amount = amount
    with pytest.raises(InvoiceInputError):
        service(session).reconcile_succeeded_attempt(attempt.id)
    assert attempt.reconciled_at is None


def test_two_attempts_apply_only_the_remaining_balance(session):
    invoice = make_invoice(session, total="10.0000")
    first = make_attempt(session, invoice, amount="4.0000")
    second = make_attempt(session, invoice, attempt_id=2, amount="6.0000")
    reconcile = service(session)
    reconcile.reconcile_succeeded_attempt(first.id)
    reconcile.reconcile_succeeded_attempt(second.id)
    assert invoice.amount_paid == Decimal("10.0000") and invoice.amount_due == Decimal("0.0000")
    assert invoice.status == "paid"


def test_claim_prevents_double_application_even_with_stale_marker(session):
    invoice = make_invoice(session)
    attempt = make_attempt(session, invoice)
    reconcile = service(session)
    reconcile.reconcile_succeeded_attempt(attempt.id)
    session.expire_all()
    assert reconcile.reconcile_succeeded_attempt(attempt.id).amount_paid == Decimal("2.5000")
    assert session.get(PaymentAttempt, attempt.id).version == 2


def test_caller_rollback_reverses_invoice_and_attempt_changes(session):
    invoice = make_invoice(session)
    attempt = make_attempt(session, invoice)
    session.commit()
    service(session).reconcile_succeeded_attempt(attempt.id)
    session.rollback()
    session.expire_all()
    assert session.get(Invoice, invoice.id).amount_paid == Decimal("0.0000")
    assert session.get(PaymentAttempt, attempt.id).reconciled_at is None


def test_caller_commit_persists_both_aggregates(session):
    invoice = make_invoice(session)
    attempt = make_attempt(session, invoice)
    service(session).reconcile_succeeded_attempt(attempt.id)
    session.commit()
    session.expire_all()
    assert session.get(Invoice, invoice.id).amount_paid == Decimal("2.5000")
    assert session.get(PaymentAttempt, attempt.id).reconciled_at.replace(tzinfo=timezone.utc) == NOW


def test_service_never_commits_or_rolls_back(session, monkeypatch):
    invoice = make_invoice(session)
    attempt = make_attempt(session, invoice)
    monkeypatch.setattr(session, "commit", lambda: pytest.fail("service committed"))
    monkeypatch.setattr(session, "rollback", lambda: pytest.fail("service rolled back"))
    service(session).reconcile_succeeded_attempt(attempt.id)
    assert session.in_transaction()


def test_real_repositories_and_mapper_configuration(session):
    configure_mappers()
    invoice = make_invoice(session)
    attempt = make_attempt(session, invoice)
    reconciliation = service(session)
    assert isinstance(reconciliation.invoices, SqlAlchemyInvoiceRepository)
    assert isinstance(reconciliation.payment_attempts, SqlAlchemyPaymentAttemptRepository)
    assert attempt.invoice is invoice
