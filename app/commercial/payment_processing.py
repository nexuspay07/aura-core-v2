"""Organization-scoped orchestration of attempts, providers, and reconciliation."""
from app.commercial.invoice_payment_reconciliation import InvoicePaymentReconciliationService
from app.commercial.models import Invoice
from app.commercial.payment_attempt_service import PaymentAttemptError, PaymentAttemptService, PaymentAttemptTransitionError
from app.commercial.payment_execution import PaymentExecutionCoordinator

class PaymentProcessingService:
 def __init__(self,session,registry,clock=None):
  self.session=session;self.registry=registry
  kwargs={} if clock is None else {'clock':clock}
  self.attempts=PaymentAttemptService(session,**kwargs);self.reconciliation=InvoicePaymentReconciliationService(session,**kwargs)
 def create_attempt(self,*,organization_id,invoice_id,provider,idempotency_key,amount,currency):
  invoice=self.session.get(Invoice,invoice_id)
  if not invoice or invoice.organization_id!=organization_id:raise PaymentAttemptError('Invoice was not found.')
  number=len(self.attempts.repo.list_by_invoice_id(invoice_id))+1
  return self.attempts.create_attempt(invoice_id=invoice_id,attempt_number=number,provider=provider,idempotency_key=idempotency_key,amount=amount,currency=currency)
 def execute(self,*,organization_id,attempt_id):
  attempt=self.attempts.repo.get_by_id(attempt_id)
  invoice=self.session.get(Invoice,attempt.invoice_id) if attempt else None
  if not attempt or not invoice or invoice.organization_id!=organization_id:raise PaymentAttemptError('Payment attempt was not found.')
  result=PaymentExecutionCoordinator(self.attempts,self.registry).execute_payment(attempt_id)
  if result.status=='succeeded':self.reconciliation.reconcile_succeeded_attempt(result.id)
  return result
 def reconcile(self,*,organization_id,attempt_id):
  attempt=self.attempts.repo.get_by_id(attempt_id)
  invoice=self.session.get(Invoice,attempt.invoice_id) if attempt else None
  if not attempt or not invoice or invoice.organization_id!=organization_id:raise PaymentAttemptError('Payment attempt was not found.')
  if attempt.status!='succeeded':raise PaymentAttemptTransitionError('Attempt is not succeeded.')
  self.reconciliation.reconcile_succeeded_attempt(attempt.id)
  return attempt
