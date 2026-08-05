from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal

from sqlalchemy import and_, desc, exists, func, or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.commercial.models import CURRENT_SUBSCRIPTION_STATUSES, Plan, PlanFeature, Subscription, SubscriptionHistory, UsageRecord, BillingAccount, UsagePrice, InvoiceUsageAllocation
from app.commercial.models import Invoice, InvoiceLineItem
from app.commercial.models import PaymentAttempt, Payment
from app.commercial.models import CreditNote
from app.commercial.models import CreditNoteApplication
from app.commercial.models import Refund

class PlanRepository(ABC):
    @abstractmethod
    def get_by_code(self, code: str) -> Plan | None: ...
    @abstractmethod
    def save(self, plan: Plan) -> Plan: ...
    @abstractmethod
    def list_active(self) -> list[Plan]: ...

class SqlAlchemyPlanRepository(PlanRepository):
    def __init__(self, session: Session): self.session = session
    def get_by_code(self, code: str) -> Plan | None: return self.session.scalar(select(Plan).where(Plan.code == code))
    def save(self, plan: Plan) -> Plan: self.session.add(plan); self.session.flush(); return plan
    def list_active(self) -> list[Plan]: return list(self.session.scalars(select(Plan).where(Plan.is_active.is_(True)).order_by(Plan.code)))

class PlanFeatureRepository(ABC):
    @abstractmethod
    def get_by_id(self, feature_id: int) -> PlanFeature | None: ...
    @abstractmethod
    def get_by_plan_and_key(self, plan_id: int, key: str) -> PlanFeature | None: ...
    @abstractmethod
    def list_for_plan(self, plan_id: int) -> list[PlanFeature]: ...
    @abstractmethod
    def save(self, feature: PlanFeature) -> PlanFeature: ...

class SqlAlchemyPlanFeatureRepository(PlanFeatureRepository):
    def __init__(self, session: Session): self.session = session
    def get_by_id(self, feature_id): return self.session.get(PlanFeature, feature_id)
    def get_by_plan_and_key(self, plan_id, key): return self.session.scalar(select(PlanFeature).where(PlanFeature.plan_id == plan_id, PlanFeature.feature_key == key))
    def list_for_plan(self, plan_id): return list(self.session.scalars(select(PlanFeature).where(PlanFeature.plan_id == plan_id).order_by(PlanFeature.feature_key)))
    def save(self, feature): self.session.add(feature); self.session.flush(); return feature


class SubscriptionRepository(ABC):
    @abstractmethod
    def save(self, subscription: Subscription) -> Subscription: ...

    @abstractmethod
    def get_by_id(self, subscription_id: int) -> Subscription | None: ...

    @abstractmethod
    def get_active_for_organization(self, organization_id: int) -> Subscription | None: ...

    @abstractmethod
    def list_for_organization(self, organization_id: int) -> list[Subscription]: ...

    @abstractmethod
    def list_for_plan(self, plan_id: int) -> list[Subscription]: ...


class SqlAlchemySubscriptionRepository(SubscriptionRepository):
    """Session-scoped repository; callers own commit and rollback boundaries."""

    def __init__(self, session: Session):
        self.session = session

    def save(self, subscription: Subscription) -> Subscription:
        if subscription.status in CURRENT_SUBSCRIPTION_STATUSES:
            current = self.get_active_for_organization(subscription.organization_id)
            if current is not None and current.id != subscription.id:
                raise ValueError("An organization may have only one active or trialing subscription.")
        self.session.add(subscription)
        self.session.flush()
        return subscription

    def get_by_id(self, subscription_id: int) -> Subscription | None:
        return self.session.get(Subscription, subscription_id)

    def get_active_for_organization(self, organization_id: int) -> Subscription | None:
        return self.session.scalar(
            select(Subscription)
            .where(
                Subscription.organization_id == organization_id,
                Subscription.status.in_(CURRENT_SUBSCRIPTION_STATUSES),
            )
            .order_by(Subscription.starts_at.desc(), Subscription.id.desc())
        )

    def list_for_organization(self, organization_id: int) -> list[Subscription]:
        return list(self.session.scalars(select(Subscription).where(Subscription.organization_id == organization_id).order_by(Subscription.starts_at.desc(), Subscription.id.desc())))

    def list_for_plan(self, plan_id: int) -> list[Subscription]:
        return list(self.session.scalars(select(Subscription).where(Subscription.plan_id == plan_id).order_by(Subscription.starts_at.desc(), Subscription.id.desc())))


class SubscriptionHistoryRepository(ABC):
    @abstractmethod
    def save(self, history: SubscriptionHistory) -> SubscriptionHistory: ...

    @abstractmethod
    def get_by_id(self, history_id: int) -> SubscriptionHistory | None: ...

    @abstractmethod
    def list_for_subscription(self, subscription_id: int) -> list[SubscriptionHistory]: ...

    @abstractmethod
    def list_by_event_type(self, event_type: str) -> list[SubscriptionHistory]: ...


class SqlAlchemySubscriptionHistoryRepository(SubscriptionHistoryRepository):
    """Append-only repository. Callers own the session transaction boundary."""

    def __init__(self, session: Session):
        self.session = session

    def save(self, history: SubscriptionHistory) -> SubscriptionHistory:
        self.session.add(history)
        self.session.flush()
        return history

    def get_by_id(self, history_id: int) -> SubscriptionHistory | None:
        return self.session.get(SubscriptionHistory, history_id)

    def list_for_subscription(self, subscription_id: int) -> list[SubscriptionHistory]:
        return list(self.session.scalars(
            select(SubscriptionHistory)
            .where(SubscriptionHistory.subscription_id == subscription_id)
            .order_by(SubscriptionHistory.effective_at, SubscriptionHistory.created_at, SubscriptionHistory.id)
        ))

    def list_by_event_type(self, event_type: str) -> list[SubscriptionHistory]:
        return list(self.session.scalars(
            select(SubscriptionHistory)
            .where(SubscriptionHistory.event_type == event_type)
            .order_by(SubscriptionHistory.effective_at, SubscriptionHistory.created_at, SubscriptionHistory.id)
        ))


class UsageRecordRepository(ABC):
    @abstractmethod
    def save(self, record: UsageRecord) -> UsageRecord: ...
    @abstractmethod
    def get_by_id(self, record_id: int) -> UsageRecord | None: ...
    @abstractmethod
    def get_by_idempotency_key(self, organization_id: int, idempotency_key: str) -> UsageRecord | None: ...
    @abstractmethod
    def list_for_organization(self, organization_id: int) -> list[UsageRecord]: ...
    @abstractmethod
    def list_for_subscription(self, subscription_id: int) -> list[UsageRecord]: ...
    @abstractmethod
    def sum_for_organization_feature(self, organization_id: int, feature_key: str, period_start: datetime, period_end: datetime) -> Decimal: ...
    @abstractmethod
    def sum_for_subscription_feature(self, subscription_id: int, feature_key: str, period_start: datetime, period_end: datetime) -> Decimal: ...
    @abstractmethod
    def list_within_period(self, organization_id: int, period_start: datetime, period_end: datetime) -> list[UsageRecord]: ...


class SqlAlchemyUsageRecordRepository(UsageRecordRepository):
    """Append-only SQL ledger repository; callers own commit and rollback."""

    def __init__(self, session: Session):
        self.session = session

    def save(self, record: UsageRecord) -> UsageRecord:
        self.session.add(record)
        self.session.flush()
        return record

    def get_by_id(self, record_id: int) -> UsageRecord | None:
        return self.session.get(UsageRecord, record_id)

    def get_by_idempotency_key(self, organization_id: int, idempotency_key: str) -> UsageRecord | None:
        return self.session.scalar(select(UsageRecord).where(UsageRecord.organization_id == organization_id, UsageRecord.idempotency_key == idempotency_key))

    def list_for_organization(self, organization_id: int) -> list[UsageRecord]:
        return list(self.session.scalars(select(UsageRecord).where(UsageRecord.organization_id == organization_id).order_by(UsageRecord.occurred_at, UsageRecord.created_at, UsageRecord.id)))

    def list_for_subscription(self, subscription_id: int) -> list[UsageRecord]:
        return list(self.session.scalars(select(UsageRecord).where(UsageRecord.subscription_id == subscription_id).order_by(UsageRecord.occurred_at, UsageRecord.created_at, UsageRecord.id)))

    def sum_for_organization_feature(self, organization_id: int, feature_key: str, period_start: datetime, period_end: datetime) -> Decimal:
        return self._sum(UsageRecord.organization_id == organization_id, feature_key, period_start, period_end)

    def sum_for_subscription_feature(self, subscription_id: int, feature_key: str, period_start: datetime, period_end: datetime) -> Decimal:
        return self._sum(UsageRecord.subscription_id == subscription_id, feature_key, period_start, period_end)

    def list_within_period(self, organization_id: int, period_start: datetime, period_end: datetime) -> list[UsageRecord]:
        return list(self.session.scalars(select(UsageRecord).where(UsageRecord.organization_id == organization_id, UsageRecord.occurred_at >= period_start, UsageRecord.occurred_at < period_end).order_by(UsageRecord.occurred_at, UsageRecord.created_at, UsageRecord.id)))

    def list_unallocated_for_subscription_period(self, organization_id: int, subscription_id: int, period_start: datetime, period_end: datetime) -> list[UsageRecord]:
        allocated = select(InvoiceUsageAllocation.id).where(InvoiceUsageAllocation.usage_record_id == UsageRecord.id)
        return list(self.session.scalars(
            select(UsageRecord).where(
                UsageRecord.organization_id == organization_id,
                UsageRecord.subscription_id == subscription_id,
                UsageRecord.occurred_at >= period_start,
                UsageRecord.occurred_at < period_end,
                ~exists(allocated),
            ).order_by(UsageRecord.occurred_at, UsageRecord.created_at, UsageRecord.id)
        ))

    def _sum(self, scope, feature_key: str, period_start: datetime, period_end: datetime) -> Decimal:
        total = self.session.scalar(select(func.coalesce(func.sum(UsageRecord.quantity), 0)).where(scope, UsageRecord.feature_key == feature_key, UsageRecord.occurred_at >= period_start, UsageRecord.occurred_at < period_end))
        return Decimal(str(total))


class UsagePriceRepository(ABC):
    @abstractmethod
    def save(self, price: UsagePrice) -> UsagePrice: ...
    @abstractmethod
    def effective_for(self, *, organization_id: int, plan_id: int, feature_key: str, unit: str, occurred_at: datetime) -> list[UsagePrice]: ...


class SqlAlchemyUsagePriceRepository(UsagePriceRepository):
    def __init__(self, session: Session): self.session = session
    def save(self, price: UsagePrice) -> UsagePrice:
        self.session.add(price); self.session.flush(); return price
    def effective_for(self, *, organization_id, plan_id, feature_key, unit, occurred_at):
        criteria = (
            UsagePrice.plan_id == plan_id,
            UsagePrice.feature_key == feature_key,
            UsagePrice.unit == unit,
            UsagePrice.is_active.is_(True),
            UsagePrice.effective_from <= occurred_at,
            or_(UsagePrice.effective_until.is_(None), UsagePrice.effective_until > occurred_at),
        )
        organization_prices = list(self.session.scalars(select(UsagePrice).where(*criteria, UsagePrice.organization_id == organization_id).order_by(UsagePrice.id)))
        if organization_prices:
            return organization_prices
        return list(self.session.scalars(select(UsagePrice).where(*criteria, UsagePrice.organization_id.is_(None)).order_by(UsagePrice.id)))


class InvoiceUsageAllocationRepository(ABC):
    @abstractmethod
    def save(self, allocation: InvoiceUsageAllocation) -> InvoiceUsageAllocation: ...
    @abstractmethod
    def get_by_usage_record_id(self, usage_record_id: int) -> InvoiceUsageAllocation | None: ...


class SqlAlchemyInvoiceUsageAllocationRepository(InvoiceUsageAllocationRepository):
    def __init__(self, session: Session): self.session = session
    def save(self, allocation: InvoiceUsageAllocation) -> InvoiceUsageAllocation:
        self.session.add(allocation); self.session.flush(); return allocation
    def get_by_usage_record_id(self, usage_record_id):
        return self.session.scalar(select(InvoiceUsageAllocation).where(InvoiceUsageAllocation.usage_record_id == usage_record_id))

class BillingAccountRepository(ABC):
    @abstractmethod
    def save(self, account: BillingAccount) -> BillingAccount: ...
    @abstractmethod
    def get_by_id(self, account_id: int) -> BillingAccount | None: ...
    @abstractmethod
    def get_by_organization_id(self, organization_id: int) -> BillingAccount | None: ...
    @abstractmethod
    def list_by_status(self, status: str) -> list[BillingAccount]: ...

class SqlAlchemyBillingAccountRepository(BillingAccountRepository):
    def __init__(self, session: Session): self.session=session
    def save(self, account):
        try:
            self.session.add(account); self.session.flush(); return account
        except Exception as exc:
            from app.commercial.billing import BillingPersistenceConflictError
            raise BillingPersistenceConflictError("Unable to persist billing account.") from exc
    def get_by_id(self, account_id): return self.session.get(BillingAccount, account_id)
    def get_by_organization_id(self, organization_id): return self.session.scalar(select(BillingAccount).where(BillingAccount.organization_id==organization_id))
    def list_by_status(self,status): return list(self.session.scalars(select(BillingAccount).where(BillingAccount.billing_status==status).order_by(BillingAccount.billing_email,BillingAccount.id)))

class InvoiceRepository(ABC):
    @abstractmethod
    def save(self, invoice: Invoice) -> Invoice: ...
    @abstractmethod
    def get_by_id(self, invoice_id: int) -> Invoice | None: ...
    @abstractmethod
    def get_by_invoice_number(self, invoice_number: str) -> Invoice | None: ...
    @abstractmethod
    def list_by_organization_id(self, organization_id: int) -> list[Invoice]: ...
    @abstractmethod
    def list_by_billing_account_id(self, billing_account_id: int) -> list[Invoice]: ...
    @abstractmethod
    def list_by_subscription_id(self, subscription_id: int) -> list[Invoice]: ...
    @abstractmethod
    def list_by_status(self, status: str) -> list[Invoice]: ...
    @abstractmethod
    def list_due_before(self, cutoff) -> list[Invoice]: ...

class SqlAlchemyInvoiceRepository(InvoiceRepository):
    def __init__(self, session: Session): self.session=session
    def save(self, invoice):
        try: self.session.add(invoice);self.session.flush();return invoice
        except Exception as exc:
            from app.commercial.billing import BillingPersistenceConflictError
            raise BillingPersistenceConflictError("Unable to persist invoice.") from exc
    def get_by_id(self,i): return self.session.get(Invoice,i)
    def get_by_invoice_number(self,n): return self.session.scalar(select(Invoice).where(Invoice.invoice_number==n))
    def list_by_organization_id(self,i): return self._list(Invoice.organization_id==i,Invoice.created_at,Invoice.id)
    def list_by_billing_account_id(self,i): return self._list(Invoice.billing_account_id==i,Invoice.created_at,Invoice.id)
    def list_by_subscription_id(self,i): return self._list(Invoice.subscription_id==i,Invoice.period_start,Invoice.id)
    def list_by_status(self,s): return self._list(Invoice.status==s,Invoice.created_at,Invoice.id)
    def list_due_before(self,c): return self._list(Invoice.due_at < c,Invoice.due_at,Invoice.id)
    def _list(self,where,*order): return list(self.session.scalars(select(Invoice).where(where).order_by(*order)))
class PaymentAttemptRepository(ABC):
 @abstractmethod
 def save(self,x):...
 @abstractmethod
 def get_by_id(self,i):...
 @abstractmethod
 def get_by_idempotency_key(self,k):...
 @abstractmethod
 def get_by_provider_reference(self,p,r):...
 @abstractmethod
 def list_by_invoice_id(self,i):...
 @abstractmethod
 def list_by_status(self,s):...
 @abstractmethod
 def list_by_provider(self,p):...
 @abstractmethod
 def list_requested_before(self,c):...
class SqlAlchemyPaymentAttemptRepository(PaymentAttemptRepository):
 def __init__(self,s):self.session=s
 def save(self,x):
  try:self.session.add(x);self.session.flush();return x
  except Exception as e:
   from app.commercial.billing import BillingPersistenceConflictError
   raise BillingPersistenceConflictError() from e
 def get_by_id(self,i):return self.session.get(PaymentAttempt,i)
 def get_by_idempotency_key(self,k):return self.session.scalar(select(PaymentAttempt).where(PaymentAttempt.idempotency_key==k))
 def get_by_provider_reference(self,p,r):return self.session.scalar(select(PaymentAttempt).where(PaymentAttempt.provider==p,PaymentAttempt.provider_reference==r))
 def list_by_invoice_id(self,i):return self._l(PaymentAttempt.invoice_id==i,PaymentAttempt.attempt_number,PaymentAttempt.id)
 def list_by_status(self,s):return self._l(PaymentAttempt.status==s,PaymentAttempt.requested_at,PaymentAttempt.id)
 def list_by_provider(self,p):return self._l(PaymentAttempt.provider==p,PaymentAttempt.requested_at,PaymentAttempt.id)
 def list_requested_before(self,c):return self._l(PaymentAttempt.requested_at<c,PaymentAttempt.requested_at,PaymentAttempt.id)
 def _l(self,w,*o):return list(self.session.scalars(select(PaymentAttempt).where(w).order_by(*o)))

class PaymentRepository(ABC):
 @abstractmethod
 def save(self,x):...
 @abstractmethod
 def get_by_attempt_id(self,i):...
 @abstractmethod
 def list_by_invoice_id(self,i):...

class SqlAlchemyPaymentRepository(PaymentRepository):
 def __init__(self,s):self.session=s
 def save(self,x):self.session.add(x);self.session.flush();return x
 def get_by_attempt_id(self,i):return self.session.scalar(select(Payment).where(Payment.payment_attempt_id==i))
 def list_by_invoice_id(self,i):return list(self.session.scalars(select(Payment).where(Payment.invoice_id==i).order_by(Payment.paid_at,Payment.id)))


class CreditNoteRepository(ABC):
 @abstractmethod
 def save(self, credit_note: CreditNote) -> CreditNote: ...
 @abstractmethod
 def get_by_id(self, credit_note_id: int) -> CreditNote | None: ...
 @abstractmethod
 def get_by_organization_and_number(self, organization_id: int, credit_note_number: str) -> CreditNote | None: ...
 @abstractmethod
 def list_by_invoice(self, invoice_id: int, *, limit: int | None = None, offset: int = 0) -> list[CreditNote]: ...
 @abstractmethod
 def list_by_organization(self, organization_id: int, *, limit: int | None = None, offset: int = 0) -> list[CreditNote]: ...


class SqlAlchemyCreditNoteRepository(CreditNoteRepository):
 """Caller-session repository for the credit-note accounting aggregate."""
 def __init__(self, session: Session): self.session = session

 def save(self, credit_note: CreditNote) -> CreditNote:
  if not isinstance(credit_note, CreditNote): self._invalid("credit_note must be a CreditNote.")
  try:
   self.session.add(credit_note); self.session.flush(); return credit_note
  except SQLAlchemyError as exc:
   from app.commercial.billing import BillingPersistenceConflictError
   raise BillingPersistenceConflictError("Unable to persist credit note.") from exc

 def get_by_id(self, credit_note_id: int) -> CreditNote | None:
  self._positive_id(credit_note_id, "credit_note_id")
  try: return self.session.get(CreditNote, credit_note_id)
  except SQLAlchemyError as exc: self._persistence_error(exc)

 def get_by_organization_and_number(self, organization_id: int, credit_note_number: str) -> CreditNote | None:
  self._positive_id(organization_id, "organization_id"); self._nonblank(credit_note_number, "credit_note_number")
  try: return self.session.scalar(select(CreditNote).where(CreditNote.organization_id == organization_id, CreditNote.credit_note_number == credit_note_number))
  except SQLAlchemyError as exc: self._persistence_error(exc)

 def list_by_invoice(self, invoice_id: int, *, limit: int | None = None, offset: int = 0) -> list[CreditNote]:
  self._positive_id(invoice_id, "invoice_id")
  return self._list(CreditNote.invoice_id == invoice_id, limit=limit, offset=offset)

 def list_by_organization(self, organization_id: int, *, limit: int | None = None, offset: int = 0) -> list[CreditNote]:
  self._positive_id(organization_id, "organization_id")
  return self._list(CreditNote.organization_id == organization_id, limit=limit, offset=offset)

 def _list(self, condition, *, limit: int | None, offset: int) -> list[CreditNote]:
  self._pagination(limit, offset)
  statement = select(CreditNote).where(condition).order_by(desc(CreditNote.created_at), desc(CreditNote.id)).offset(offset)
  if limit is not None: statement = statement.limit(limit)
  try: return list(self.session.scalars(statement))
  except SQLAlchemyError as exc: self._persistence_error(exc)

 @staticmethod
 def _positive_id(value, name: str) -> None:
  if isinstance(value, bool) or not isinstance(value, int) or value <= 0: SqlAlchemyCreditNoteRepository._invalid(f"{name} must be a positive integer.")

 @staticmethod
 def _nonblank(value, name: str) -> None:
  if not isinstance(value, str) or not value.strip(): SqlAlchemyCreditNoteRepository._invalid(f"{name} must be non-blank.")

 @staticmethod
 def _pagination(limit, offset) -> None:
  if limit is not None and (isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0): SqlAlchemyCreditNoteRepository._invalid("limit must be a positive integer or None.")
  if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0: SqlAlchemyCreditNoteRepository._invalid("offset must be a non-negative integer.")

 @staticmethod
 def _invalid(message: str) -> None:
  from app.commercial.billing import BillingError
  raise BillingError(message)

 @staticmethod
 def _persistence_error(exc: Exception) -> None:
  from app.commercial.billing import BillingPersistenceConflictError
  raise BillingPersistenceConflictError("Unable to query credit notes.") from exc

class CreditNoteApplicationRepository(ABC):
 @abstractmethod
 def save(self, application: CreditNoteApplication) -> CreditNoteApplication: ...
 @abstractmethod
 def get_by_id(self, application_id: int) -> CreditNoteApplication|None: ...
 @abstractmethod
 def get_by_organization_and_idempotency_key(self, organization_id: int, idempotency_key: str) -> CreditNoteApplication|None: ...
 @abstractmethod
 def list_by_credit_note(self, credit_note_id: int, *, limit=None, offset=0) -> list[CreditNoteApplication]: ...
 @abstractmethod
 def list_by_invoice(self, invoice_id: int, *, limit=None, offset=0) -> list[CreditNoteApplication]: ...

class SqlAlchemyCreditNoteApplicationRepository(CreditNoteApplicationRepository):
 def __init__(self,session:Session):self.session=session
 def save(self,x):
  if not isinstance(x,CreditNoteApplication): SqlAlchemyCreditNoteRepository._invalid("application must be a CreditNoteApplication.")
  try:self.session.add(x);self.session.flush();return x
  except SQLAlchemyError as exc:
   from app.commercial.billing import BillingPersistenceConflictError
   raise BillingPersistenceConflictError("Unable to persist credit application.") from exc
 def get_by_id(self,i):
  SqlAlchemyCreditNoteRepository._positive_id(i,"application_id")
  try:return self.session.get(CreditNoteApplication,i)
  except SQLAlchemyError as exc:SqlAlchemyCreditNoteRepository._persistence_error(exc)
 def get_by_organization_and_idempotency_key(self,o,k):
  SqlAlchemyCreditNoteRepository._positive_id(o,"organization_id");SqlAlchemyCreditNoteRepository._nonblank(k,"idempotency_key")
  try:return self.session.scalar(select(CreditNoteApplication).where(CreditNoteApplication.organization_id==o,CreditNoteApplication.idempotency_key==k))
  except SQLAlchemyError as exc:SqlAlchemyCreditNoteRepository._persistence_error(exc)
 def list_by_credit_note(self,i,*,limit=None,offset=0):return self._list(CreditNoteApplication.credit_note_id,i,limit,offset,"credit_note_id")
 def list_by_invoice(self,i,*,limit=None,offset=0):return self._list(CreditNoteApplication.invoice_id,i,limit,offset,"invoice_id")
 def _list(self,col,i,limit,offset,name):
  SqlAlchemyCreditNoteRepository._positive_id(i,name);SqlAlchemyCreditNoteRepository._pagination(limit,offset)
  q=select(CreditNoteApplication).where(col==i).order_by(desc(CreditNoteApplication.created_at),desc(CreditNoteApplication.id)).offset(offset)
  if limit is not None:q=q.limit(limit)
  try:return list(self.session.scalars(q))
  except SQLAlchemyError as exc:SqlAlchemyCreditNoteRepository._persistence_error(exc)

class RefundRepository(ABC):
 @abstractmethod
 def save(self,refund:Refund)->Refund:...
 @abstractmethod
 def get_by_id(self,refund_id:int)->Refund|None:...
 @abstractmethod
 def get_by_organization_and_number(self,organization_id:int,refund_number:str)->Refund|None:...
 @abstractmethod
 def get_by_organization_and_idempotency_key(self,organization_id:int,idempotency_key:str)->Refund|None:...
 @abstractmethod
 def list_by_invoice(self,invoice_id:int,*,limit=None,offset=0)->list[Refund]:...
 @abstractmethod
 def list_by_payment_attempt(self,payment_attempt_id:int,*,limit=None,offset=0)->list[Refund]:...
 @abstractmethod
 def list_by_credit_note(self,credit_note_id:int,*,limit=None,offset=0)->list[Refund]:...
 @abstractmethod
 def list_by_organization(self,organization_id:int,*,limit=None,offset=0)->list[Refund]:...
class SqlAlchemyRefundRepository(RefundRepository):
 def __init__(self,session:Session):self.session=session
 def save(self,x):
  if not isinstance(x,Refund):SqlAlchemyCreditNoteRepository._invalid('refund must be a Refund.')
  try:self.session.add(x);self.session.flush();return x
  except SQLAlchemyError as e:
   from app.commercial.billing import BillingPersistenceConflictError
   raise BillingPersistenceConflictError('Unable to persist refund.') from e
 def get_by_id(self,i):
  SqlAlchemyCreditNoteRepository._positive_id(i,'refund_id')
  try:return self.session.get(Refund,i)
  except SQLAlchemyError as e:SqlAlchemyCreditNoteRepository._persistence_error(e)
 def get_by_organization_and_number(self,o,n):return self._scoped(o,n,Refund.refund_number,'refund_number')
 def get_by_organization_and_idempotency_key(self,o,k):return self._scoped(o,k,Refund.idempotency_key,'idempotency_key')
 def _scoped(self,o,value,column,name):
  SqlAlchemyCreditNoteRepository._positive_id(o,'organization_id');SqlAlchemyCreditNoteRepository._nonblank(value,name)
  try:return self.session.scalar(select(Refund).where(Refund.organization_id==o,column==value))
  except SQLAlchemyError as e:SqlAlchemyCreditNoteRepository._persistence_error(e)
 def list_by_invoice(self,i,*,limit=None,offset=0):return self._list(Refund.invoice_id,i,limit,offset,'invoice_id')
 def list_by_payment_attempt(self,i,*,limit=None,offset=0):return self._list(Refund.payment_attempt_id,i,limit,offset,'payment_attempt_id')
 def list_by_credit_note(self,i,*,limit=None,offset=0):return self._list(Refund.credit_note_id,i,limit,offset,'credit_note_id')
 def list_by_organization(self,i,*,limit=None,offset=0):return self._list(Refund.organization_id,i,limit,offset,'organization_id')
 def _list(self,column,i,limit,offset,name):
  SqlAlchemyCreditNoteRepository._positive_id(i,name);SqlAlchemyCreditNoteRepository._pagination(limit,offset);q=select(Refund).where(column==i).order_by(desc(Refund.requested_at),desc(Refund.created_at),desc(Refund.id)).offset(offset)
  if limit is not None:q=q.limit(limit)
  try:return list(self.session.scalars(q))
  except SQLAlchemyError as e:SqlAlchemyCreditNoteRepository._persistence_error(e)
