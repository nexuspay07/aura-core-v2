from dataclasses import dataclass,field
from decimal import Decimal
class PaymentProviderError(Exception):pass
class PaymentProviderNotFoundError(PaymentProviderError):pass
class PaymentProviderUnavailableError(PaymentProviderError):pass
class PaymentProviderRejectedError(PaymentProviderError):pass
@dataclass(frozen=True)
class PaymentProviderRequest:
 payment_attempt_id:int;idempotency_key:str;amount:Decimal;currency:str;provider_reference:str|None=None;metadata:dict=field(default_factory=dict)
 def __post_init__(self):
  if self.payment_attempt_id<=0 or not self.idempotency_key.strip() or isinstance(self.amount,float) or Decimal(self.amount)<=0 or len(self.currency)!=3 or not self.currency.isupper():raise PaymentProviderError()
@dataclass(frozen=True)
class PaymentProviderResult:
 status:str;provider_reference:str|None=None;failure_code:str|None=None;failure_message:str|None=None;provider_metadata:dict=field(default_factory=dict)
 def __post_init__(self):
  if self.status not in {'succeeded','failed','processing'} or self.status=='succeeded' and not self.provider_reference:raise PaymentProviderError()
class PaymentProviderRegistry:
 def __init__(self):self._p={}
 def register(self,p):
  n=p.provider_name.strip().lower()
  if not n or n in self._p:raise PaymentProviderError()
  self._p[n]=p
 def get(self,n):
  try:return self._p[n.strip().lower()]
  except:raise PaymentProviderNotFoundError()
 def contains(self,n):return n.strip().lower() in self._p
 def list_provider_names(self):return sorted(self._p)
class FakePaymentProvider:
 provider_name='fake'
 def __init__(self,outcome='succeeded'):self.outcome=outcome;self.requests=[];self._results={};self.execution_count=0
 def execute_payment(self,r):
  if r.idempotency_key in self._results:
   old,request=self._results[r.idempotency_key]
   if (request.amount,request.currency,request.payment_attempt_id)!=(r.amount,r.currency,r.payment_attempt_id):raise PaymentProviderError()
   return old
  if self.outcome=='unavailable':raise PaymentProviderUnavailableError()
  if self.outcome=='rejected':raise PaymentProviderRejectedError()
  self.execution_count+=1;self.requests.append(r);status=self.outcome;result=PaymentProviderResult(status,'fake-'+str(r.payment_attempt_id) if status in {'succeeded','processing'} else None,'failed' if status=='failed' else None,'failed' if status=='failed' else None);self._results[r.idempotency_key]=(result,r);return result
