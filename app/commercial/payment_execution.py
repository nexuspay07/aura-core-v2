from app.commercial.payment_providers import PaymentProviderRequest,PaymentProviderUnavailableError,PaymentProviderRejectedError
from app.commercial.payment_attempt_service import PaymentAttemptTransitionError
class PaymentExecutionCoordinator:
 def __init__(self,service,registry):self.service=service;self.registry=registry
 def execute_payment(self,attempt_id):
  a=self.service.repo.get_by_id(attempt_id)
  if not a or a.status!='pending':raise PaymentAttemptTransitionError()
  provider=self.registry.get(a.provider);r=PaymentProviderRequest(a.id,a.idempotency_key,a.amount,a.currency,a.provider_reference,a.provider_metadata_json or {})
  self.service.start_processing(a.id)
  try:result=provider.execute_payment(r)
  except PaymentProviderUnavailableError:return a
  except PaymentProviderRejectedError:return self.service.mark_failed(a.id,'provider_rejected','Provider rejected request')
  if result.status=='succeeded':return self.service.mark_succeeded(a.id,result.provider_reference)
  if result.status=='failed':return self.service.mark_failed(a.id,result.failure_code,result.failure_message)
  return a
