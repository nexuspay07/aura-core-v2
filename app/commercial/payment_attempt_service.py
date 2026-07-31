from datetime import datetime,timezone
from decimal import Decimal
from app.commercial.models import Invoice,PaymentAttempt
from app.commercial.repositories import SqlAlchemyPaymentAttemptRepository
class PaymentAttemptError(Exception):pass
class PaymentAttemptTransitionError(PaymentAttemptError):pass
class PaymentAttemptService:
 def __init__(self,s,clock=lambda:datetime.now(timezone.utc)):self.session=s;self.repo=SqlAlchemyPaymentAttemptRepository(s);self.clock=clock
 def create_attempt(self,**v):
  if not self.session.get(Invoice,v['invoice_id']) or not v['provider'].strip() or len(v['currency'])!=3 or not v['currency'].isupper() or Decimal(v['amount'])<=0 or not v['idempotency_key'].strip():raise PaymentAttemptError()
  v['status']='pending';v['requested_at']=self.clock();return self.repo.save(PaymentAttempt(**v))
 def _go(self,i,from_,to,field,**v):
  x=self.repo.get_by_id(i)
  if not x or x.status not in from_:raise PaymentAttemptTransitionError()
  x.status=to;setattr(x,field,self.clock());x.version+=1
  for k,z in v.items():setattr(x,k,z)
  return self.repo.save(x)
 def start_processing(self,i):return self._go(i,{'pending'},'processing','processing_at')
 def mark_succeeded(self,i,provider_reference=None):return self._go(i,{'processing'},'succeeded','succeeded_at',provider_reference=provider_reference)
 def mark_failed(self,i,failure_code=None,failure_message=None):return self._go(i,{'processing'},'failed','failed_at',failure_code=failure_code,failure_message=failure_message)
 def cancel_attempt(self,i):return self._go(i,{'pending','processing'},'cancelled','cancelled_at')
