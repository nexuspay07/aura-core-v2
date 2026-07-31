"""Durable, idempotent application of issued credit notes to invoice balances."""
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from sqlalchemy import update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.commercial.billing import BillingError, BillingPersistenceConflictError
from app.commercial.models import CreditNote, CreditNoteApplication, Invoice
from app.commercial.repositories import CreditNoteRepository,InvoiceRepository,CreditNoteApplicationRepository,SqlAlchemyCreditNoteRepository,SqlAlchemyInvoiceRepository,SqlAlchemyCreditNoteApplicationRepository

Q=Decimal("0.0001"); Z=Decimal("0.0000")
@dataclass(frozen=True)
class CreditApplicationResult: application:CreditNoteApplication; credit_note:CreditNote; invoice:Invoice
class CreditApplicationService:
 """An exact replay returns the existing durable application without mutation."""
 def __init__(self,session:Session,*,credit_note_repository:CreditNoteRepository|None=None,invoice_repository:InvoiceRepository|None=None,application_repository:CreditNoteApplicationRepository|None=None,clock=lambda:datetime.now(timezone.utc)):
  self.session=session;self.notes=credit_note_repository or SqlAlchemyCreditNoteRepository(session);self.invoices=invoice_repository or SqlAlchemyInvoiceRepository(session);self.apps=application_repository or SqlAlchemyCreditNoteApplicationRepository(session);self.clock=clock
 def apply_credit(self,credit_note_id,*,amount,idempotency_key):
  self._id(credit_note_id);amount=self._positive(amount);self._key(idempotency_key)
  note=self._note(credit_note_id);invoice=self._invoice(note.invoice_id)
  existing=self.apps.get_by_organization_and_idempotency_key(note.organization_id,idempotency_key)
  if existing:
   if (existing.credit_note_id,existing.invoice_id,existing.amount,existing.currency)==(note.id,invoice.id,amount,note.currency):return CreditApplicationResult(existing,note,invoice)
   raise BillingPersistenceConflictError("Idempotency key conflicts with an existing credit application.")
  if note.status!="issued":raise BillingError("Only issued credit notes can be applied.")
  if invoice.organization_id!=note.organization_id or invoice.currency!=note.currency:raise BillingError("Credit note does not match its invoice.")
  if invoice.status not in {"open","paid"}:raise BillingError("Invoice cannot receive credit.")
  if amount>self._money(note.amount_remaining) or amount>self._money(invoice.amount_due):raise BillingError("Credit amount exceeds available balance.")
  now=self._now(); app=CreditNoteApplication(organization_id=note.organization_id,credit_note_id=note.id,invoice_id=invoice.id,idempotency_key=idempotency_key,amount=amount,currency=note.currency,applied_at=now,created_at=now,version=1)
  self.apps.save(app)
  new_applied=self._money(note.amount_applied+amount);new_remaining=self._money(note.total-new_applied);new_due=self._money(invoice.amount_due-amount);status="fully_applied" if new_remaining==Z else "issued"
  try:
   a=self.session.execute(update(CreditNote).where(CreditNote.id==note.id,CreditNote.version==note.version,CreditNote.status=="issued",CreditNote.amount_remaining>=amount).values(amount_applied=new_applied,amount_remaining=new_remaining,status=status,version=CreditNote.version+1,updated_at=now))
   b=self.session.execute(update(Invoice).where(Invoice.id==invoice.id,Invoice.version==invoice.version,Invoice.amount_due>=amount).values(amount_due=new_due,version=Invoice.version+1,updated_at=now))
  except SQLAlchemyError as exc:raise BillingPersistenceConflictError("Unable to claim credit application.") from exc
  if a.rowcount!=1 or b.rowcount!=1:raise BillingPersistenceConflictError("Concurrent credit application conflict.")
  self.session.expire(note);self.session.expire(invoice)
  return CreditApplicationResult(app,self.notes.get_by_id(note.id),self.invoices.get_by_id(invoice.id))
 def _note(self,i):
  try:x=self.notes.get_by_id(i)
  except SQLAlchemyError as e:raise BillingPersistenceConflictError() from e
  if not x:raise BillingError("Credit note not found.")
  return x
 def _invoice(self,i):
  try:x=self.invoices.get_by_id(i)
  except SQLAlchemyError as e:raise BillingPersistenceConflictError() from e
  if not x:raise BillingError("Invoice not found.")
  return x
 @staticmethod
 def _id(i):
  if isinstance(i,bool) or not isinstance(i,int) or i<=0:raise BillingError("credit_note_id must be positive.")
 @staticmethod
 def _key(k):
  if not isinstance(k,str) or not k.strip():raise BillingError("idempotency_key must be non-blank.")
 @staticmethod
 def _money(x):
  if isinstance(x,float):raise BillingError("Float money is not allowed.")
  try:return Decimal(x).quantize(Q,rounding=ROUND_HALF_UP)
  except (InvalidOperation,TypeError,ValueError) as e:raise BillingError("Invalid monetary value.") from e
 @classmethod
 def _positive(cls,x):
  x=cls._money(x)
  if x<=Z:raise BillingError("amount must be positive.")
  return x
 def _now(self):
  x=self.clock()
  if not isinstance(x,datetime) or x.tzinfo is None:raise BillingError("Clock must be timezone aware.")
  return x.astimezone(timezone.utc)
