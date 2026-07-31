from dataclasses import dataclass
from decimal import Decimal,ROUND_HALF_UP
Q=Decimal('0.0001')
class InvoiceCalculationError(Exception):pass
@dataclass(frozen=True)
class LineItemCalculationResult: subtotal_amount:Decimal;tax_amount:Decimal;discount_amount:Decimal;total_amount:Decimal
@dataclass(frozen=True)
class InvoiceCalculationResult: subtotal_amount:Decimal;tax_amount:Decimal;discount_amount:Decimal;total_amount:Decimal;amount_paid:Decimal;amount_due:Decimal;line_items:tuple
class InvoiceCalculationEngine:
 def _d(self,x):
  if isinstance(x,float):raise InvoiceCalculationError()
  try:return Decimal(x).quantize(Q,rounding=ROUND_HALF_UP)
  except:raise InvoiceCalculationError()
 def calculate_line_item(self,x):
  q,u,t,d=map(self._d,(x.quantity,x.unit_amount,x.tax_amount,x.discount_amount))
  if q<0 or t<0 or d<0:raise InvoiceCalculationError()
  s=(q*u).quantize(Q,rounding=ROUND_HALF_UP);total=(s+t-d).quantize(Q,rounding=ROUND_HALF_UP)
  if total<0:raise InvoiceCalculationError()
  return LineItemCalculationResult(s,t,d,total)
 def calculate_invoice(self,i):
  lines=tuple(self.calculate_line_item(x) for x in i.line_items);s=sum((x.subtotal_amount for x in lines),Decimal(0)).quantize(Q);t=sum((x.tax_amount for x in lines),Decimal(0)).quantize(Q);d=sum((x.discount_amount for x in lines),Decimal(0)).quantize(Q);total=(s+t-d).quantize(Q);paid=self._d(i.amount_paid)
  if paid<0 or paid>total:raise InvoiceCalculationError()
  return InvoiceCalculationResult(s,t,d,total,paid,(total-paid).quantize(Q),lines)
 def apply_calculation(self,i):
  if i.status!='draft':raise InvoiceCalculationError()
  r=self.calculate_invoice(i)
  for x,z in zip(i.line_items,r.line_items):x.subtotal_amount=z.subtotal_amount;x.total_amount=z.total_amount
  i.subtotal_amount=r.subtotal_amount;i.tax_amount=r.tax_amount;i.discount_amount=r.discount_amount;i.total_amount=r.total_amount;i.amount_due=r.amount_due;i.version+=1
  return r
