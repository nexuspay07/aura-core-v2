from decimal import Decimal
from types import SimpleNamespace
import pytest
from app.commercial.invoice_calculation import *
def line(**v):
 x=dict(quantity=Decimal('2'),unit_amount=Decimal('12.3456'),tax_amount=Decimal('1'),discount_amount=Decimal('0'));x.update(v);return SimpleNamespace(**x)
def test_line_and_invoice_calculation():
 e=InvoiceCalculationEngine();r=e.calculate_line_item(line());assert r.subtotal_amount==Decimal('24.6912') and r.total_amount==Decimal('25.6912')
 i=SimpleNamespace(line_items=[line()],amount_paid=Decimal('5'),status='draft',version=1);z=e.calculate_invoice(i);assert z.amount_due==Decimal('20.6912');e.apply_calculation(i);assert i.version==2 and i.total_amount==z.total_amount
@pytest.mark.parametrize('v',[1.0,Decimal('-1')])
def test_invalid(v):
 with pytest.raises(InvoiceCalculationError):InvoiceCalculationEngine().calculate_line_item(line(quantity=v))
