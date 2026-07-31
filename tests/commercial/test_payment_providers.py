from decimal import Decimal
import pytest
from app.commercial.payment_providers import *
def req(k='k'):return PaymentProviderRequest(1,k,Decimal('1'),'CAD')
def test_request_result_registry_fake():
 r=req();p=FakePaymentProvider();x=p.execute_payment(r);assert x.status=='succeeded' and p.execute_payment(r)==x and p.execution_count==1
 reg=PaymentProviderRegistry();reg.register(p);assert reg.get('FAKE') is p and reg.list_provider_names()==['fake']
def test_validation_and_outcomes():
 with pytest.raises(PaymentProviderError):PaymentProviderRequest(0,'',Decimal('0'),'cad')
 with pytest.raises(PaymentProviderError):PaymentProviderResult('succeeded')
 with pytest.raises(PaymentProviderUnavailableError):FakePaymentProvider('unavailable').execute_payment(req())
