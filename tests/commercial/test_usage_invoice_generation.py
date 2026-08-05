from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, event, insert, select
from sqlalchemy.orm import sessionmaker

from app.commercial.models import BillingAccount, InvoiceUsageAllocation, Plan, Subscription, UsagePrice, UsageRecord
from app.commercial.usage_invoice_generation import UsageInvoiceConflictError, UsageInvoiceGenerationService, UsagePriceConflictError, UsagePriceService
from app.db.database import Base
from app.db.organization_table import organization_table
from app.db.user_table import user_table


UTC = timezone.utc
START = datetime(2026, 1, 1, tzinfo=UTC)
END = datetime(2026, 2, 1, tzinfo=UTC)


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    event.listen(engine, "connect", lambda dbapi, _: dbapi.execute("PRAGMA foreign_keys=ON"))
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    s.execute(insert(user_table).values(id=1, email="usage-billing@example.test", password_hash="test"))
    s.execute(insert(organization_table).values(id=1, name="Aura", slug="usage-billing", owner_user_id=1, plan="free", subscription_status="inactive", is_active=True))
    s.add_all([
        Plan(id=1, code="usage-billing", name="Usage Billing", seat_limit=1),
        BillingAccount(id=1, organization_id=1, billing_email="billing@example.test", billing_name="Aura", country_code="CA", currency="CAD"),
        Subscription(id=1, organization_id=1, plan_id=1, status="active", billing_cycle="monthly", starts_at=START),
    ])
    s.commit()
    yield s
    s.close(); engine.dispose()


def record(session, key="calls", quantity="2", occurred_at=datetime(2026, 1, 5, tzinfo=UTC), unit="request"):
    item = UsageRecord(organization_id=1, subscription_id=1, feature_key=key, quantity=Decimal(quantity), unit=unit, occurred_at=occurred_at)
    session.add(item); session.flush(); return item


def price(session, **overrides):
    value = dict(plan_id=1, feature_key="calls", unit="request", currency="CAD", unit_price=Decimal("0.125000"), effective_from=START)
    value.update(overrides)
    item = UsagePrice(**value); session.add(item); session.flush(); return item


def test_effective_price_selection_organization_override_and_missing(session):
    record(session); plan_price = price(session); override = price(session, organization_id=1, unit_price=Decimal("0.200000")); session.commit()
    service = UsageInvoiceGenerationService(session)
    assert service.prices.effective_for(organization_id=1, plan_id=1, feature_key="calls", unit="request", occurred_at=datetime(2026, 1, 5, tzinfo=UTC)) == [override]
    invoice = service.generate(organization_id=1, subscription_id=1, period_start=START, period_end=END)
    assert invoice.total_amount == Decimal("0.40") and invoice.currency == "CAD"
    assert plan_price.id != override.id


def test_usage_price_service_rejects_overlapping_effective_prices(session):
    service = UsagePriceService(session)
    service.create_price(plan_id=1, feature_key="calls", unit="request", currency="CAD", unit_price=Decimal("0.1"), effective_from=START)
    with pytest.raises(UsagePriceConflictError):
        service.create_price(plan_id=1, feature_key="calls", unit="request", currency="CAD", unit_price=Decimal("0.2"), effective_from=datetime(2026, 1, 2, tzinfo=UTC))


def test_missing_overlapping_and_currency_incompatible_prices_are_rejected(session):
    record(session)
    with pytest.raises(UsageInvoiceConflictError):
        UsageInvoiceGenerationService(session).generate(organization_id=1, subscription_id=1, period_start=START, period_end=END)
    price(session, currency="USD")
    with pytest.raises(UsageInvoiceConflictError):
        UsageInvoiceGenerationService(session).generate(organization_id=1, subscription_id=1, period_start=START, period_end=END)
    session.rollback(); record(session); price(session); price(session, unit_price=Decimal("0.2"))
    with pytest.raises(UsageInvoiceConflictError):
        UsageInvoiceGenerationService(session).generate(organization_id=1, subscription_id=1, period_start=START, period_end=END)


def test_generation_groups_allocates_rounds_and_is_idempotent(session):
    first = record(session, quantity="1.3333")
    second = record(session, quantity="2.6667")
    price(session, unit_price=Decimal("0.125000")); session.commit()
    service = UsageInvoiceGenerationService(session)
    invoice = service.generate(organization_id=1, subscription_id=1, period_start=START, period_end=END)
    assert invoice.status == "draft" and invoice.subtotal_amount == Decimal("0.50")
    assert len(invoice.line_items) == 1 and invoice.line_items[0].quantity == Decimal("4.0000")
    allocations = list(session.scalars(select(InvoiceUsageAllocation).order_by(InvoiceUsageAllocation.usage_record_id)))
    assert [a.usage_record_id for a in allocations] == [first.id, second.id]
    assert sum((a.amount for a in allocations), Decimal("0")) == invoice.total_amount
    assert service.generate(organization_id=1, subscription_id=1, period_start=START, period_end=END).id == invoice.id
    assert session.query(InvoiceUsageAllocation).count() == 2


def test_generation_rollback_leaves_usage_unallocated(session):
    usage = record(session); price(session); session.commit()
    invoice = UsageInvoiceGenerationService(session).generate(organization_id=1, subscription_id=1, period_start=START, period_end=END)
    session.rollback()
    assert session.get(InvoiceUsageAllocation, 1) is None
    assert session.get(UsageRecord, usage.id) is not None
    assert invoice.id is not None


def test_bulk_thousand_usage_records_are_aggregated(session):
    session.add_all(UsageRecord(organization_id=1, subscription_id=1, feature_key="calls", quantity=Decimal("1"), unit="request", occurred_at=datetime(2026, 1, 5, tzinfo=UTC)) for _ in range(1000))
    price(session, unit_price=Decimal("0.010000")); session.commit()
    invoice = UsageInvoiceGenerationService(session).generate(organization_id=1, subscription_id=1, period_start=START, period_end=END)
    assert invoice.total_amount == Decimal("10.00")
    assert session.query(InvoiceUsageAllocation).count() == 1000
