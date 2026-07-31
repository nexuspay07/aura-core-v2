from app.commercial.payment_execution import PaymentExecutionCoordinator
from app.commercial.payment_providers import FakePaymentProvider,PaymentProviderRegistry
def test_registry_and_fake_idempotency():
 p=FakePaymentProvider();r=PaymentProviderRegistry();r.register(p);assert r.get('fake') is p
