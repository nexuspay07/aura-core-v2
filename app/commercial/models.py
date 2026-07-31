from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, JSON, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base
from app.db.organization_orm import Organization


SUBSCRIPTION_STATUSES = ("pending", "trialing", "active", "past_due", "paused", "cancelled", "expired")
BILLING_CYCLES = ("monthly", "annual", "custom")
CURRENT_SUBSCRIPTION_STATUSES = ("active", "trialing")
SUBSCRIPTION_HISTORY_EVENT_TYPES = (
    "created", "activated", "trial_started", "trial_ended", "plan_changed",
    "paused", "resumed", "cancelled", "expired", "renewed", "payment_status_changed",
)
SUBSCRIPTION_HISTORY_ACTOR_TYPES = ("system", "user", "organization", "external")

class Plan(Base):
    __tablename__ = "plans"
    __table_args__ = (UniqueConstraint("code", name="uq_plans_code"), CheckConstraint("seat_limit >= 0", name="ck_plans_seat_limit"))
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    seat_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    features: Mapped[list["PlanFeature"]] = relationship(back_populates="plan", lazy="select", cascade="all, delete-orphan")
    subscriptions: Mapped[list["Subscription"]] = relationship(
        back_populates="plan", lazy="select", passive_deletes=True
    )

class PlanFeature(Base):
    __tablename__ = "plan_features"
    __table_args__ = (UniqueConstraint("plan_id", "feature_key", name="uq_plan_features_plan_key"), CheckConstraint("value_type IN ('boolean','integer','decimal','string')", name="ck_plan_features_value_type"), CheckConstraint("integer_value IS NULL OR integer_value >= 0", name="ck_plan_features_integer_nonnegative"), CheckConstraint("decimal_value IS NULL OR decimal_value >= 0", name="ck_plan_features_decimal_nonnegative"))
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id", ondelete="CASCADE"), nullable=False, index=True)
    feature_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    value_type: Mapped[str] = mapped_column(String(16), nullable=False)
    boolean_value: Mapped[bool | None] = mapped_column(Boolean)
    integer_value: Mapped[int | None] = mapped_column(Integer)
    decimal_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    string_value: Mapped[str | None] = mapped_column(String(512))
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    plan: Mapped[Plan] = relationship(back_populates="features", lazy="select")


class Subscription(Base):
    """Persistent commercial relationship between one organization and one plan.

    Current-subscription uniqueness is enforced by the repository before flush.
    This portable application invariant is not concurrency-safe across independent
    transactions; a future production policy may add a dialect-specific guard.
    """

    __tablename__ = "subscriptions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','trialing','active','past_due','paused','cancelled','expired')",
            name="ck_subscriptions_status",
        ),
        CheckConstraint(
            "billing_cycle IN ('monthly','annual','custom')",
            name="ck_subscriptions_billing_cycle",
        ),
        CheckConstraint("ends_at IS NULL OR ends_at >= starts_at", name="ck_subscriptions_ends_after_start"),
        CheckConstraint("renews_at IS NULL OR renews_at >= starts_at", name="ck_subscriptions_renews_after_start"),
        CheckConstraint("cancelled_at IS NULL OR cancelled_at >= starts_at", name="ck_subscriptions_cancelled_after_start"),
        CheckConstraint("trial_ends_at IS NULL OR trial_ends_at >= starts_at", name="ck_subscriptions_trial_after_start"),
        CheckConstraint(
            "trial_ends_at IS NULL OR ends_at IS NULL OR trial_ends_at <= ends_at",
            name="ck_subscriptions_trial_before_end",
        ),
        CheckConstraint("version > 0", name="ck_subscriptions_version_positive"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    billing_cycle: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    renews_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    external_reference: Mapped[str | None] = mapped_column(String(255), index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    organization: Mapped[Organization] = relationship(back_populates="subscriptions", lazy="select")
    plan: Mapped[Plan] = relationship(back_populates="subscriptions", lazy="select")
    history: Mapped[list["SubscriptionHistory"]] = relationship(
        back_populates="subscription",
        lazy="select",
        passive_deletes=True,
        order_by="SubscriptionHistory.effective_at, SubscriptionHistory.created_at, SubscriptionHistory.id",
    )
    usage_records: Mapped[list["UsageRecord"]] = relationship(
        back_populates="subscription", lazy="select", passive_deletes=True
    )
    invoices: Mapped[list["Invoice"]] = relationship("Invoice", back_populates="subscription", lazy="select", passive_deletes=True)


class SubscriptionHistory(Base):
    """Append-only audit record; Subscription remains the current-state authority.

    The repository deliberately exposes no update or delete operation. Database
    users with direct write access can still modify records, so this is a
    repository-boundary guarantee rather than database-level immutability.
    """

    __tablename__ = "subscription_history"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('created','activated','trial_started','trial_ended','plan_changed','paused','resumed','cancelled','expired','renewed','payment_status_changed')",
            name="ck_subscription_history_event_type",
        ),
        CheckConstraint(
            "previous_status IS NULL OR previous_status IN ('pending','trialing','active','past_due','paused','cancelled','expired')",
            name="ck_subscription_history_previous_status",
        ),
        CheckConstraint(
            "new_status IS NULL OR new_status IN ('pending','trialing','active','past_due','paused','cancelled','expired')",
            name="ck_subscription_history_new_status",
        ),
        CheckConstraint(
            "actor_type IS NULL OR actor_type IN ('system','user','organization','external')",
            name="ck_subscription_history_actor_type",
        ),
        CheckConstraint(
            "event_type IN ('created','renewed','payment_status_changed') OR previous_status IS NOT NULL OR new_status IS NOT NULL OR previous_plan_id IS NOT NULL OR new_plan_id IS NOT NULL",
            name="ck_subscription_history_change_values",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subscription_id: Mapped[int] = mapped_column(ForeignKey("subscriptions.id"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    previous_status: Mapped[str | None] = mapped_column(String(16))
    new_status: Mapped[str | None] = mapped_column(String(16))
    previous_plan_id: Mapped[int | None] = mapped_column(ForeignKey("plans.id"))
    new_plan_id: Mapped[int | None] = mapped_column(ForeignKey("plans.id"))
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    reason: Mapped[str | None] = mapped_column(String(512))
    actor_type: Mapped[str | None] = mapped_column(String(16))
    actor_id: Mapped[str | None] = mapped_column(String(255))
    external_reference: Mapped[str | None] = mapped_column(String(255), index=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    subscription: Mapped[Subscription] = relationship(back_populates="history", lazy="select")


class UsageRecord(Base):
    """Append-only commercial consumption ledger entry.

    Idempotency is database-enforced per organization and non-null key. The
    service validates that the referenced subscription belongs to the same
    organization because that cross-table invariant is not portable here.
    """

    __tablename__ = "usage_records"
    __table_args__ = (
        UniqueConstraint("organization_id", "idempotency_key", name="uq_usage_records_organization_idempotency"),
        CheckConstraint("quantity > 0", name="ck_usage_records_quantity_positive"),
        CheckConstraint(
            "source_type IS NULL OR source_type IN ('api','system','workspace','user')",
            name="ck_usage_records_source_type",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    subscription_id: Mapped[int] = mapped_column(ForeignKey("subscriptions.id"), nullable=False, index=True)
    feature_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(64), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(255), index=True)
    source_type: Mapped[str | None] = mapped_column(String(16))
    source_id: Mapped[str | None] = mapped_column(String(255))
    metadata_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    organization: Mapped[Organization] = relationship(back_populates="usage_records", lazy="select")
    subscription: Mapped[Subscription] = relationship(back_populates="usage_records", lazy="select")

class BillingAccount(Base):
    __tablename__="billing_accounts"
    __table_args__=(UniqueConstraint("organization_id",name="uq_billing_accounts_organization"),CheckConstraint("billing_status IN ('active','suspended','closed')",name="ck_billing_accounts_status"),CheckConstraint("version > 0",name="ck_billing_accounts_version_positive"))
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    organization_id: Mapped[int]=mapped_column(ForeignKey("organizations.id"),nullable=False,index=True)
    billing_email: Mapped[str]=mapped_column(String(255),nullable=False,index=True)
    billing_name: Mapped[str]=mapped_column(String(255),nullable=False)
    company_name: Mapped[str|None]=mapped_column(String(255)); address_line_1: Mapped[str|None]=mapped_column(String(255)); address_line_2: Mapped[str|None]=mapped_column(String(255)); city: Mapped[str|None]=mapped_column(String(100)); region: Mapped[str|None]=mapped_column(String(100)); postal_code: Mapped[str|None]=mapped_column(String(32))
    country_code: Mapped[str]=mapped_column(String(2),nullable=False)
    currency: Mapped[str]=mapped_column(String(3),nullable=False,index=True)
    tax_identifier: Mapped[str|None]=mapped_column(String(128))
    billing_status: Mapped[str]=mapped_column(String(16),nullable=False,default="active",index=True)
    version: Mapped[int]=mapped_column(Integer,nullable=False,default=1)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc),nullable=False)
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc),nullable=False)
    organization: Mapped[Organization]=relationship(back_populates="billing_account",lazy="select")
    invoices: Mapped[list["Invoice"]]=relationship(back_populates="billing_account",lazy="select",passive_deletes=True)

class Invoice(Base):
 __tablename__="invoices"
 __table_args__=(UniqueConstraint("invoice_number",name="uq_invoices_number"),CheckConstraint("status IN ('draft','open','paid','void','uncollectible')",name="ck_invoices_status"),CheckConstraint("version > 0",name="ck_invoices_version"),CheckConstraint("amount_paid >= 0",name="ck_invoices_paid"),CheckConstraint("period_end > period_start",name="ck_invoices_period"))
 id:Mapped[int]=mapped_column(Integer,primary_key=True);organization_id:Mapped[int]=mapped_column(ForeignKey("organizations.id"),nullable=False,index=True);billing_account_id:Mapped[int]=mapped_column(ForeignKey("billing_accounts.id"),nullable=False,index=True);subscription_id:Mapped[int]=mapped_column(ForeignKey("subscriptions.id"),nullable=False,index=True);invoice_number:Mapped[str]=mapped_column(String(64),nullable=False);status:Mapped[str]=mapped_column(String(16),nullable=False,default="draft",index=True);currency:Mapped[str]=mapped_column(String(3),nullable=False);period_start:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False);period_end:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)
 subtotal_amount:Mapped[Decimal]=mapped_column(Numeric(18,4),nullable=False,default=0);tax_amount:Mapped[Decimal]=mapped_column(Numeric(18,4),nullable=False,default=0);discount_amount:Mapped[Decimal]=mapped_column(Numeric(18,4),nullable=False,default=0);total_amount:Mapped[Decimal]=mapped_column(Numeric(18,4),nullable=False,default=0);amount_due:Mapped[Decimal]=mapped_column(Numeric(18,4),nullable=False,default=0);amount_paid:Mapped[Decimal]=mapped_column(Numeric(18,4),nullable=False,default=0)
 due_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True),index=True);issued_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True));paid_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True));voided_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True));version:Mapped[int]=mapped_column(Integer,nullable=False,default=1);created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc),nullable=False);updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc),nullable=False)
 organization:Mapped[Organization]=relationship(back_populates="invoices",lazy="select");billing_account:Mapped[BillingAccount]=relationship(back_populates="invoices",lazy="select");subscription:Mapped[Subscription]=relationship(back_populates="invoices",lazy="select");line_items:Mapped[list["InvoiceLineItem"]]=relationship(back_populates="invoice",cascade="all, delete-orphan",order_by="InvoiceLineItem.line_number",lazy="select")
 payment_attempts:Mapped[list["PaymentAttempt"]]=relationship(back_populates="invoice",cascade="all, delete-orphan",order_by="PaymentAttempt.attempt_number",lazy="select")
 credit_notes:Mapped[list["CreditNote"]]=relationship(back_populates="invoice",lazy="select",passive_deletes=True)
 credit_note_applications:Mapped[list["CreditNoteApplication"]]=relationship(back_populates="invoice",lazy="select",passive_deletes=True)
 refunds:Mapped[list["Refund"]]=relationship(back_populates="invoice",lazy="select",passive_deletes=True)
class InvoiceLineItem(Base):
 __tablename__="invoice_line_items";__table_args__=(UniqueConstraint("invoice_id","line_number",name="uq_invoice_lines_number"),CheckConstraint("item_type IN ('subscription','usage','adjustment','credit','tax','discount')",name="ck_invoice_lines_type"),CheckConstraint("quantity >= 0",name="ck_invoice_lines_quantity"),CheckConstraint("period_end IS NULL OR period_start IS NULL OR period_end > period_start",name="ck_invoice_lines_period"))
 id:Mapped[int]=mapped_column(Integer,primary_key=True);invoice_id:Mapped[int]=mapped_column(ForeignKey("invoices.id",ondelete="CASCADE"),nullable=False,index=True);line_number:Mapped[int]=mapped_column(Integer,nullable=False);item_type:Mapped[str]=mapped_column(String(16),nullable=False);description:Mapped[str]=mapped_column(String(512),nullable=False);quantity:Mapped[Decimal]=mapped_column(Numeric(18,4),nullable=False);unit_amount:Mapped[Decimal]=mapped_column(Numeric(18,4),nullable=False);subtotal_amount:Mapped[Decimal]=mapped_column(Numeric(18,4),nullable=False);tax_amount:Mapped[Decimal]=mapped_column(Numeric(18,4),nullable=False);discount_amount:Mapped[Decimal]=mapped_column(Numeric(18,4),nullable=False);total_amount:Mapped[Decimal]=mapped_column(Numeric(18,4),nullable=False);period_start:Mapped[datetime|None]=mapped_column(DateTime(timezone=True));period_end:Mapped[datetime|None]=mapped_column(DateTime(timezone=True));source_type:Mapped[str|None]=mapped_column(String(64));source_id:Mapped[str|None]=mapped_column(String(255));metadata_json:Mapped[dict|None]=mapped_column(JSON);created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc),nullable=False);updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc),nullable=False);invoice:Mapped[Invoice]=relationship(back_populates="line_items",lazy="select")
class PaymentAttempt(Base):
 __tablename__="payment_attempts";__table_args__=(UniqueConstraint("idempotency_key",name="uq_payment_attempts_idempotency"),UniqueConstraint("invoice_id","attempt_number",name="uq_payment_attempts_invoice_number"),CheckConstraint("attempt_number > 0",name="ck_payment_attempt_number"),CheckConstraint("amount > 0",name="ck_payment_attempt_amount"),CheckConstraint("version >= 1",name="ck_payment_attempt_version"),CheckConstraint("status IN ('pending','processing','succeeded','failed','cancelled')",name="ck_payment_attempt_status"))
 id:Mapped[int]=mapped_column(Integer,primary_key=True);invoice_id:Mapped[int]=mapped_column(ForeignKey("invoices.id",ondelete="CASCADE"),nullable=False,index=True);attempt_number:Mapped[int]=mapped_column(Integer,nullable=False);provider:Mapped[str]=mapped_column(String(64),nullable=False,index=True);provider_reference:Mapped[str|None]=mapped_column(String(255),index=True);idempotency_key:Mapped[str]=mapped_column(String(255),nullable=False);status:Mapped[str]=mapped_column(String(16),nullable=False,default="pending",index=True);amount:Mapped[Decimal]=mapped_column(Numeric(18,4),nullable=False);currency:Mapped[str]=mapped_column(String(3),nullable=False);failure_code:Mapped[str|None]=mapped_column(String(128));failure_message:Mapped[str|None]=mapped_column(String(512));provider_metadata_json:Mapped[dict|None]=mapped_column(JSON);requested_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,index=True);processing_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True));succeeded_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True));failed_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True));cancelled_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True));reconciled_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True));version:Mapped[int]=mapped_column(Integer,nullable=False,default=1);created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc),nullable=False);updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc),nullable=False);invoice:Mapped[Invoice]=relationship(back_populates="payment_attempts",lazy="select");refunds:Mapped[list["Refund"]]=relationship(back_populates="payment_attempt",lazy="select",passive_deletes=True)

class CreditNote(Base):
 __tablename__="credit_notes"
 __table_args__=(
  UniqueConstraint("organization_id","credit_note_number",name="uq_credit_notes_organization_number"),
  CheckConstraint("status IN ('draft','issued','fully_applied','void')",name="ck_credit_notes_status"),
  CheckConstraint("subtotal >= 0",name="ck_credit_notes_subtotal_nonnegative"),
  CheckConstraint("tax >= 0",name="ck_credit_notes_tax_nonnegative"),
  CheckConstraint("total >= 0",name="ck_credit_notes_total_nonnegative"),
  CheckConstraint("amount_applied >= 0",name="ck_credit_notes_applied_nonnegative"),
  CheckConstraint("amount_remaining >= 0",name="ck_credit_notes_remaining_nonnegative"),
  CheckConstraint("amount_applied <= total",name="ck_credit_notes_applied_not_over_total"),
  CheckConstraint("amount_remaining <= total",name="ck_credit_notes_remaining_not_over_total"),
  CheckConstraint("amount_applied + amount_remaining <= total",name="ck_credit_notes_balance_not_over_total"),
  CheckConstraint("version > 0",name="ck_credit_notes_version"),
 )
 id:Mapped[int]=mapped_column(Integer,primary_key=True)
 organization_id:Mapped[int]=mapped_column(ForeignKey("organizations.id"),nullable=False,index=True)
 invoice_id:Mapped[int]=mapped_column(ForeignKey("invoices.id"),nullable=False,index=True)
 credit_note_number:Mapped[str]=mapped_column(String(64),nullable=False)
 status:Mapped[str]=mapped_column(String(16),nullable=False,default="draft",index=True)
 currency:Mapped[str]=mapped_column(String(3),nullable=False)
 reason:Mapped[str|None]=mapped_column(String(512))
 subtotal:Mapped[Decimal]=mapped_column(Numeric(18,4),nullable=False,default=lambda:Decimal("0"))
 tax:Mapped[Decimal]=mapped_column(Numeric(18,4),nullable=False,default=lambda:Decimal("0"))
 total:Mapped[Decimal]=mapped_column(Numeric(18,4),nullable=False,default=lambda:Decimal("0"))
 amount_applied:Mapped[Decimal]=mapped_column(Numeric(18,4),nullable=False,default=lambda:Decimal("0"))
 amount_remaining:Mapped[Decimal]=mapped_column(Numeric(18,4),nullable=False,default=lambda:Decimal("0"))
 issued_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
 voided_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
 created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc),nullable=False)
 updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc),nullable=False)
 version:Mapped[int]=mapped_column(Integer,nullable=False,default=1)
 organization:Mapped[Organization]=relationship(back_populates="credit_notes",lazy="select")
 invoice:Mapped[Invoice]=relationship(back_populates="credit_notes",lazy="select")
 line_items:Mapped[list["CreditNoteLineItem"]]=relationship(back_populates="credit_note",order_by="CreditNoteLineItem.line_number",lazy="select",passive_deletes=True)
 applications:Mapped[list["CreditNoteApplication"]]=relationship(back_populates="credit_note",lazy="select",passive_deletes=True)
 refunds:Mapped[list["Refund"]]=relationship(back_populates="credit_note",lazy="select",passive_deletes=True)

class CreditNoteLineItem(Base):
 __tablename__="credit_note_line_items"
 __table_args__=(UniqueConstraint("credit_note_id","line_number",name="uq_credit_note_lines_number"),CheckConstraint("line_number > 0",name="ck_credit_note_lines_number_positive"),CheckConstraint("quantity >= 0",name="ck_credit_note_lines_quantity_nonnegative"))
 id:Mapped[int]=mapped_column(Integer,primary_key=True)
 credit_note_id:Mapped[int]=mapped_column(ForeignKey("credit_notes.id"),nullable=False,index=True)
 line_number:Mapped[int]=mapped_column(Integer,nullable=False)
 description:Mapped[str]=mapped_column(String(512),nullable=False)
 quantity:Mapped[Decimal]=mapped_column(Numeric(18,4),nullable=False)
 unit_amount:Mapped[Decimal]=mapped_column(Numeric(18,4),nullable=False)
 subtotal:Mapped[Decimal]=mapped_column(Numeric(18,4),nullable=False)
 tax:Mapped[Decimal]=mapped_column(Numeric(18,4),nullable=False)
 total:Mapped[Decimal]=mapped_column(Numeric(18,4),nullable=False)
 created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc),nullable=False)
 credit_note:Mapped[CreditNote]=relationship(back_populates="line_items",lazy="select")

class CreditNoteApplication(Base):
 __tablename__="credit_note_applications"
 __table_args__=(UniqueConstraint("organization_id","idempotency_key",name="uq_credit_note_applications_organization_key"),CheckConstraint("amount > 0",name="ck_credit_note_applications_amount_positive"),CheckConstraint("version > 0",name="ck_credit_note_applications_version"))
 id:Mapped[int]=mapped_column(Integer,primary_key=True)
 organization_id:Mapped[int]=mapped_column(ForeignKey("organizations.id"),nullable=False,index=True)
 credit_note_id:Mapped[int]=mapped_column(ForeignKey("credit_notes.id"),nullable=False,index=True)
 invoice_id:Mapped[int]=mapped_column(ForeignKey("invoices.id"),nullable=False,index=True)
 idempotency_key:Mapped[str]=mapped_column(String(255),nullable=False)
 amount:Mapped[Decimal]=mapped_column(Numeric(18,4),nullable=False)
 currency:Mapped[str]=mapped_column(String(3),nullable=False)
 applied_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)
 created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)
 version:Mapped[int]=mapped_column(Integer,nullable=False,default=1)
 organization:Mapped[Organization]=relationship(back_populates="credit_note_applications",lazy="select")
 credit_note:Mapped[CreditNote]=relationship(back_populates="applications",lazy="select")
 invoice:Mapped[Invoice]=relationship(back_populates="credit_note_applications",lazy="select")

class Refund(Base):
 __tablename__="refunds"
 __table_args__=(UniqueConstraint("organization_id","refund_number",name="uq_refunds_organization_number"),UniqueConstraint("organization_id","idempotency_key",name="uq_refunds_organization_key"),CheckConstraint("amount > 0",name="ck_refunds_amount_positive"),CheckConstraint("status IN ('pending','processing','succeeded','failed','cancelled')",name="ck_refunds_status"),CheckConstraint("version > 0",name="ck_refunds_version"))
 id:Mapped[int]=mapped_column(Integer,primary_key=True);organization_id:Mapped[int]=mapped_column(ForeignKey("organizations.id"),nullable=False,index=True);invoice_id:Mapped[int]=mapped_column(ForeignKey("invoices.id"),nullable=False,index=True);payment_attempt_id:Mapped[int]=mapped_column(ForeignKey("payment_attempts.id"),nullable=False,index=True);credit_note_id:Mapped[int|None]=mapped_column(ForeignKey("credit_notes.id"),index=True);refund_number:Mapped[str]=mapped_column(String(64),nullable=False);status:Mapped[str]=mapped_column(String(16),nullable=False,default="pending",index=True);amount:Mapped[Decimal]=mapped_column(Numeric(18,4),nullable=False);currency:Mapped[str]=mapped_column(String(3),nullable=False);reason:Mapped[str|None]=mapped_column(String(512));idempotency_key:Mapped[str]=mapped_column(String(255),nullable=False);provider:Mapped[str]=mapped_column(String(64),nullable=False,index=True);provider_reference:Mapped[str|None]=mapped_column(String(255),index=True);failure_code:Mapped[str|None]=mapped_column(String(128));failure_message:Mapped[str|None]=mapped_column(String(512));requested_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False,index=True);processing_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True));succeeded_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True));failed_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True));cancelled_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True));reconciled_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True));created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc),nullable=False);updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc),nullable=False);version:Mapped[int]=mapped_column(Integer,nullable=False,default=1)
 organization:Mapped[Organization]=relationship(back_populates="refunds",lazy="select");invoice:Mapped[Invoice]=relationship(back_populates="refunds",lazy="select");payment_attempt:Mapped[PaymentAttempt]=relationship(back_populates="refunds",lazy="select");credit_note:Mapped[CreditNote|None]=relationship(back_populates="refunds",lazy="select")
