from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.api.auth_routes import get_current_user_from_token
from app.commercial.invoice_service import InvoiceService,InvoiceNotFoundError,InvoiceInputError,InvoiceTransitionError
from app.commercial.repositories import SqlAlchemyInvoiceRepository

router=APIRouter(prefix='/commercial/invoices',tags=['Commercial Invoices'])
security=HTTPBearer()
def get_session():
 s=SessionLocal()
 try:yield s
 finally:s.close()
class InvoiceCreate(BaseModel):
 organization_id:int;billing_account_id:int;subscription_id:int;invoice_number:str;currency:str;period_start:datetime;period_end:datetime;subtotal_amount:Decimal=Decimal('0');tax_amount:Decimal=Decimal('0');discount_amount:Decimal=Decimal('0');total_amount:Decimal=Decimal('0');amount_due:Decimal=Decimal('0');amount_paid:Decimal=Decimal('0')
class InvoiceOut(BaseModel):
 id:int;organization_id:int;invoice_number:str;status:str;currency:str;amount_due:Decimal;amount_paid:Decimal;version:int
 class Config:from_attributes=True
class InvoiceUpdate(BaseModel):
 currency:str|None=None;due_at:datetime|None=None
async def current(credentials:HTTPAuthorizationCredentials=Depends(security)):
 return await get_current_user_from_token(credentials)
def organization_id(user):
 if not user.get('organization'): raise HTTPException(403,'No active organization')
 return user['organization']['id']
def owned(invoice,user):
 if not invoice or invoice.organization_id!=organization_id(user): raise HTTPException(404,'Invoice not found')
 return invoice
def write(s,fn):
 try:
  value=fn();s.commit();s.refresh(value);return value
 except HTTPException: s.rollback();raise
 except Exception: s.rollback();raise
def service(s):return InvoiceService(s)
def fail(fn):
 try:return fn()
 except InvoiceNotFoundError:raise HTTPException(404,'Invoice not found')
 except (InvoiceInputError,InvoiceTransitionError):raise HTTPException(409,'Invoice operation rejected')
@router.get('',response_model=list[InvoiceOut])
def list_invoices(s:Session=Depends(get_session),user=Depends(current)):
 return SqlAlchemyInvoiceRepository(s).list_by_organization_id(organization_id(user))
@router.get('/{invoice_id}',response_model=InvoiceOut)
def get_invoice(invoice_id:int,s:Session=Depends(get_session),user=Depends(current)):
 return owned(SqlAlchemyInvoiceRepository(s).get_by_id(invoice_id),user)
@router.post('',response_model=InvoiceOut,status_code=201)
def create_invoice(body:InvoiceCreate,s:Session=Depends(get_session),user=Depends(current)):
 data=body.model_dump();data['organization_id']=organization_id(user);return write(s,lambda:fail(lambda:service(s).create_invoice(**data)))
@router.patch('/{invoice_id}',response_model=InvoiceOut)
def update_invoice(invoice_id:int,body:InvoiceUpdate,s:Session=Depends(get_session),user=Depends(current)):
 x=owned(SqlAlchemyInvoiceRepository(s).get_by_id(invoice_id),user)
 for k in ('due_at','currency'):
  if getattr(body,k) is not None:setattr(x,k,getattr(body,k))
 return write(s,lambda:x)
@router.post('/{invoice_id}/issue',response_model=InvoiceOut)
def issue(invoice_id:int,s:Session=Depends(get_session),user=Depends(current)):
 owned(SqlAlchemyInvoiceRepository(s).get_by_id(invoice_id),user);return write(s,lambda:fail(lambda:service(s).issue_invoice(invoice_id)))
@router.post('/{invoice_id}/void',response_model=InvoiceOut)
def void(invoice_id:int,s:Session=Depends(get_session),user=Depends(current)):
 owned(SqlAlchemyInvoiceRepository(s).get_by_id(invoice_id),user);return write(s,lambda:fail(lambda:service(s).void_invoice(invoice_id)))
