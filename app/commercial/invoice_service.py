from datetime import datetime,timezone
from decimal import Decimal
from app.commercial.models import Invoice,InvoiceLineItem,BillingAccount,Subscription
from app.commercial.repositories import SqlAlchemyInvoiceRepository
from app.db.organization_orm import Organization
class InvoiceError(Exception):pass
class InvoiceNotFoundError(InvoiceError):pass
class InvoiceInputError(InvoiceError):pass
class InvoiceTransitionError(InvoiceError):pass
class InvoiceService:
 def __init__(self,session,clock=lambda:datetime.now(timezone.utc)):self.session=session;self.repo=SqlAlchemyInvoiceRepository(session);self.clock=clock
 def create_invoice(self,**v):
  if not self.session.get(Organization,v['organization_id']) or not self.session.get(BillingAccount,v['billing_account_id']) or not self.session.get(Subscription,v['subscription_id']):raise InvoiceInputError()
  if not v['invoice_number'].strip() or len(v['currency'])!=3 or not v['currency'].isupper() or v['period_end']<=v['period_start']:raise InvoiceInputError()
  return self.repo.save(Invoice(**v))
 def add_line_item(self,invoice_id,**v):
  i=self.repo.get_by_id(invoice_id)
  if not i:raise InvoiceNotFoundError()
  if i.status!='draft' or v['line_number']<=0 or not v['description'].strip() or v['quantity']<0 or v['discount_amount']<0:raise InvoiceInputError()
  x=InvoiceLineItem(invoice_id=i.id,**v);self.session.add(x);self.session.flush();i.version+=1;return x
 def issue_invoice(self,i):
  x=self.repo.get_by_id(i)
  if not x or x.status!='draft' or not x.line_items:raise InvoiceTransitionError()
  x.status='open';x.issued_at=self.clock();x.version+=1;return self.repo.save(x)
 def record_payment(self,i,amount):
  x=self.repo.get_by_id(i);amount=Decimal(amount)
  if not x or x.status!='open' or amount<=0 or x.amount_paid+amount>x.amount_due:raise InvoiceTransitionError()
  x.amount_paid+=amount;x.version+=1
  if x.amount_paid==x.amount_due:x.status='paid';x.paid_at=self.clock()
  return self.repo.save(x)
 def mark_uncollectible(self,i):
  x=self.repo.get_by_id(i)
  if not x or x.status!='open':raise InvoiceTransitionError()
  x.status='uncollectible';x.version+=1;return self.repo.save(x)
 def void_invoice(self,i):
  x=self.repo.get_by_id(i)
  if not x or x.status not in {'draft','open'}:raise InvoiceTransitionError()
  x.status='void';x.voided_at=self.clock();x.version+=1;return self.repo.save(x)
