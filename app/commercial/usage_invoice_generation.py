"""Usage aggregation and draft invoice generation.

The service is deliberately transaction-neutral: its caller commits or rolls
back the invoice, line items, and immutable allocation ledger together.
"""
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session

from app.commercial.models import BillingAccount, Invoice, InvoiceLineItem, Subscription, UsagePrice, InvoiceUsageAllocation
from app.commercial.repositories import (
    SqlAlchemyInvoiceRepository,
    SqlAlchemyInvoiceUsageAllocationRepository,
    SqlAlchemyUsagePriceRepository,
    SqlAlchemyUsageRecordRepository,
)
from app.db.organization_orm import Organization


class UsageInvoiceGenerationError(Exception):
    pass


class UsageInvoiceInputError(UsageInvoiceGenerationError):
    pass


class UsageInvoiceConflictError(UsageInvoiceGenerationError):
    pass


class UsagePriceInputError(UsageInvoiceGenerationError):
    pass


class UsagePriceConflictError(UsageInvoiceGenerationError):
    pass


class UsagePriceService:
    """Creates effective-dated prices; it intentionally exposes no mutation API."""

    def __init__(self, session: Session):
        self.session = session
        self.prices = SqlAlchemyUsagePriceRepository(session)

    def create_price(self, **values) -> UsagePrice:
        currency = values.get("currency", "")
        start = values.get("effective_from")
        end = values.get("effective_until")
        if not currency.isupper() or len(currency) != 3 or not values.get("feature_key") or not values.get("unit"):
            raise UsagePriceInputError("Usage price fields are invalid.")
        if start is None or start.tzinfo is None or (end is not None and (end.tzinfo is None or end <= start)):
            raise UsagePriceInputError("Usage price effective dates are invalid.")
        if Decimal(values.get("unit_price")) < 0:
            raise UsagePriceInputError("Unit price cannot be negative.")
        candidates = self.session.query(UsagePrice).filter(
            UsagePrice.plan_id == values["plan_id"],
            UsagePrice.feature_key == values["feature_key"],
            UsagePrice.unit == values["unit"],
            UsagePrice.organization_id.is_(None) if values.get("organization_id") is None else UsagePrice.organization_id == values["organization_id"],
            UsagePrice.is_active.is_(True),
        ).all()
        for candidate in candidates:
            candidate_end = candidate.effective_until
            if (candidate_end is None or candidate_end > start) and (end is None or end > candidate.effective_from):
                raise UsagePriceConflictError("Effective usage prices may not overlap.")
        return self.prices.save(UsagePrice(**values))


class UsageInvoiceGenerationService:
    """Creates a draft invoice from all currently unallocated period usage."""

    def __init__(self, session: Session, *, clock=lambda: datetime.now(timezone.utc)):
        self.session = session
        self.clock = clock
        self.invoices = SqlAlchemyInvoiceRepository(session)
        self.records = SqlAlchemyUsageRecordRepository(session)
        self.prices = SqlAlchemyUsagePriceRepository(session)
        self.allocations = SqlAlchemyInvoiceUsageAllocationRepository(session)

    def generate(self, *, organization_id: int, subscription_id: int, period_start: datetime, period_end: datetime) -> Invoice:
        self._period(period_start, period_end)
        organization = self.session.get(Organization, organization_id)
        subscription = self.session.get(Subscription, subscription_id)
        billing_account = self.session.scalar(self.session.query(BillingAccount).filter(BillingAccount.organization_id == organization_id).statement)
        if organization is None or subscription is None or subscription.organization_id != organization_id:
            raise UsageInvoiceInputError("The subscription is not available to this organization.")
        if billing_account is None or billing_account.billing_status != "active":
            raise UsageInvoiceInputError("An active billing account is required.")
        if subscription.status not in {"active", "trialing"}:
            raise UsageInvoiceConflictError("Only current subscriptions are eligible for usage billing.")

        invoice_number = self._invoice_number(organization_id, subscription_id, period_start, period_end)
        existing = self.invoices.get_by_invoice_number(invoice_number)
        if existing is not None:
            if existing.organization_id != organization_id or existing.subscription_id != subscription_id:
                raise UsageInvoiceConflictError("Usage invoice idempotency key collision.")
            return existing

        records = self.records.list_unallocated_for_subscription_period(organization_id, subscription_id, period_start, period_end)
        if not records:
            raise UsageInvoiceConflictError("No eligible usage exists for this billing period.")

        priced = []
        for record in records:
            matches = self.prices.effective_for(organization_id=organization_id, plan_id=subscription.plan_id, feature_key=record.feature_key, unit=record.unit, occurred_at=record.occurred_at)
            if len(matches) != 1:
                raise UsageInvoiceConflictError("Usage requires exactly one effective price.")
            price = matches[0]
            if price.currency != billing_account.currency:
                raise UsageInvoiceConflictError("Usage price currency must match the billing account currency.")
            if self.allocations.get_by_usage_record_id(record.id) is not None:
                raise UsageInvoiceConflictError("Usage has already been invoiced.")
            amount = self._money(record.quantity * price.unit_price)
            priced.append((record, price, amount))

        grouped: dict[tuple[str, str, Decimal, str], list[tuple]] = {}
        for item in priced:
            record, price, _ = item
            grouped.setdefault((record.feature_key, record.unit, price.unit_price, price.currency), []).append(item)
        total = self._money(sum((amount for _, _, amount in priced), Decimal("0")))
        invoice = Invoice(
            organization_id=organization_id, billing_account_id=billing_account.id, subscription_id=subscription_id,
            invoice_number=invoice_number, status="draft", currency=billing_account.currency,
            period_start=period_start, period_end=period_end, subtotal_amount=total, tax_amount=Decimal("0"),
            discount_amount=Decimal("0"), total_amount=total, amount_due=total, amount_paid=Decimal("0"),
            created_at=self.clock(), updated_at=self.clock(),
        )
        self.invoices.save(invoice)
        for line_number, ((feature_key, unit, unit_price, currency), entries) in enumerate(grouped.items(), start=1):
            quantity = sum((record.quantity for record, _, _ in entries), Decimal("0"))
            line_total = self._money(sum((amount for _, _, amount in entries), Decimal("0")))
            line = InvoiceLineItem(
                invoice_id=invoice.id, line_number=line_number, item_type="usage",
                description=f"Usage: {feature_key} ({unit})", quantity=quantity, unit_amount=unit_price,
                subtotal_amount=line_total, tax_amount=Decimal("0"), discount_amount=Decimal("0"), total_amount=line_total,
                period_start=period_start, period_end=period_end, source_type="usage", source_id=feature_key,
                metadata_json={"feature_key": feature_key, "unit": unit, "currency": currency},
                created_at=self.clock(), updated_at=self.clock(),
            )
            self.session.add(line)
            self.session.flush()
            for record, price, amount in entries:
                self.allocations.save(InvoiceUsageAllocation(
                    organization_id=organization_id, usage_record_id=record.id, invoice_id=invoice.id,
                    invoice_line_item_id=line.id, quantity_allocated=record.quantity, unit_price=price.unit_price,
                    currency=currency, amount=amount, created_at=self.clock(),
                ))
        return invoice

    @staticmethod
    def _money(amount: Decimal) -> Decimal:
        return Decimal(amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @staticmethod
    def _period(start: datetime, end: datetime) -> None:
        if start.tzinfo is None or end.tzinfo is None or end <= start:
            raise UsageInvoiceInputError("Billing periods must be aware, half-open UTC intervals.")

    @staticmethod
    def _invoice_number(organization_id: int, subscription_id: int, start: datetime, end: datetime) -> str:
        return f"USAGE-{organization_id}-{subscription_id}-{start.astimezone(timezone.utc):%Y%m%d%H%M%S}-{end.astimezone(timezone.utc):%Y%m%d%H%M%S}"
