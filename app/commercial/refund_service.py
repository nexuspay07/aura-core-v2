from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from sqlalchemy import func, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.commercial.billing import BillingError, BillingPersistenceConflictError
from app.commercial.models import Refund, Invoice, PaymentAttempt, CreditNote
from app.commercial.repositories import SqlAlchemyRefundRepository

class RefundService:
 def __init__(self,session:Session,refund_repository=None,clock=lambda:datetime.now(timezone.utc)):
  self.session=session;self.refunds=refund_repository or SqlAlchemyRefundRepository(session);self.clock=clock
 def create_refund(self,*,organization_id,invoice_id,payment_attempt_id,amount,currency,reason=None,idempotency_key,provider,provider_reference=None,credit_note_id=None,refund_number=None,requested_at=None):
  self._id(organization_id);self._id(invoice_id);self._id(payment_attempt_id);self._key(idempotency_key);self._key(provider);self._key(refund_number);amount=self._amount(amount)
  invoice=self.session.get(Invoice,invoice_id);attempt=self.session.get(PaymentAttempt,payment_attempt_id)
  if not invoice or not attempt:raise BillingError('Related invoice or payment attempt was not found.')
  if invoice.organization_id!=organization_id or attempt.invoice_id!=invoice_id or attempt.status!='succeeded' or currency!=invoice.currency or currency!=attempt.currency:raise BillingError('Invalid refund relationship or currency.')
  note=None
  if credit_note_id is not None:
   self._id(credit_note_id);note=self.session.get(CreditNote,credit_note_id)
   if not note or note.organization_id!=organization_id or note.invoice_id!=invoice_id or note.currency!=currency or note.status not in {'issued','fully_applied'}:raise BillingError('Invalid credit note.')
  old=self.refunds.get_by_organization_and_idempotency_key(organization_id,idempotency_key)
  if old:
   if (old.invoice_id,old.payment_attempt_id,old.credit_note_id,old.amount,old.currency,old.reason,old.provider)==(invoice_id,payment_attempt_id,credit_note_id,amount,currency,reason,provider):return old
   raise BillingPersistenceConflictError('Conflicting idempotency key.')
  active=self.session.scalar(select(func.coalesce(func.sum(Refund.amount),0)).where(Refund.payment_attempt_id==payment_attempt_id,Refund.status.in_(['pending','processing','succeeded'])))
  if amount>Decimal(attempt.amount)-Decimal(active):raise BillingError('Refund exceeds refundable amount.')
  now=self._now(requested_at);claim=self.session.execute(update(PaymentAttempt).where(PaymentAttempt.id==attempt.id,PaymentAttempt.version==attempt.version,PaymentAttempt.status=='succeeded').values(version=PaymentAttempt.version+1,updated_at=now))
  if claim.rowcount!=1:raise BillingPersistenceConflictError('Concurrent refund conflict.')
  return self.refunds.save(Refund(organization_id=organization_id,invoice_id=invoice_id,payment_attempt_id=payment_attempt_id,credit_note_id=credit_note_id,refund_number=refund_number,status='pending',amount=amount,currency=currency,reason=reason,idempotency_key=idempotency_key,provider=provider,provider_reference=provider_reference,requested_at=now,created_at=now,updated_at=now,version=1))
 def mark_processing(self,i,*,organization_id,expected_version,provider_reference=None,processing_at=None):return self._transition(i,organization_id,expected_version,{'pending'},'processing','processing_at',processing_at,provider_reference=provider_reference)
 def mark_succeeded(self,i,*,organization_id,expected_version,provider_reference=None,succeeded_at=None):return self._transition(i,organization_id,expected_version,{'pending','processing'},'succeeded','succeeded_at',succeeded_at,provider_reference=provider_reference,failure_code=None,failure_message=None)
 def mark_failed(self,i,*,organization_id,expected_version,failure_code=None,failure_message=None,failed_at=None):return self._transition(i,organization_id,expected_version,{'pending','processing'},'failed','failed_at',failed_at,failure_code=failure_code,failure_message=failure_message)
 def cancel_refund(self,i,*,organization_id,expected_version,cancelled_at=None):return self._transition(i,organization_id,expected_version,{'pending'},'cancelled','cancelled_at',cancelled_at)
 def _transition(self,i,o,v,states,status,field,at,**values):
  self._id(i);self._id(o);self._id(v);now=self._now(at);q=update(Refund).where(Refund.id==i,Refund.organization_id==o,Refund.version==v,Refund.status.in_(states)).values(status=status,version=Refund.version+1,updated_at=now,**{field:now},**{k:x for k,x in values.items() if x is not None or k.startswith('failure_')})
  if self.session.execute(q).rowcount!=1:raise BillingPersistenceConflictError('Invalid refund transition or stale version.')
  return self.refunds.get_by_id(i)
 @staticmethod
 def _id(x):
  if isinstance(x,bool) or not isinstance(x,int) or x<=0:raise BillingError('Identifier must be positive.')
 @staticmethod
 def _key(x):
  if not isinstance(x,str) or not x.strip():raise BillingError('Required text is blank.')
 @staticmethod
 def _amount(x):
  if isinstance(x,bool) or isinstance(x,float):raise BillingError('Invalid refund amount.')
  try:x=Decimal(x)
  except (InvalidOperation,TypeError,ValueError) as e:raise BillingError('Invalid refund amount.') from e
  if not x.is_finite() or x<=0 or x.as_tuple().exponent < -4:raise BillingError('Invalid refund amount.')
  return x.quantize(Decimal('0.0001'))
 def _now(self,x):
  x=x or self.clock()
  if not isinstance(x,datetime) or x.tzinfo is None:raise BillingError('Timestamp must be timezone-aware.')
  return x.astimezone(timezone.utc)
