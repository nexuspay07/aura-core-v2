from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session
from app.api.auth_routes import get_current_user_from_token
from app.commercial.payment_attempt_service import PaymentAttemptError, PaymentAttemptTransitionError
from app.commercial.payment_processing import PaymentProcessingService
from app.commercial.payment_providers import FakePaymentProvider, PaymentProviderRegistry
from app.commercial.repositories import SqlAlchemyInvoiceRepository, SqlAlchemyPaymentAttemptRepository
from app.db.database import SessionLocal

router=APIRouter(prefix='/commercial',tags=['Commercial Payments']);security=HTTPBearer()
def get_session():
 s=SessionLocal()
 try:yield s
 finally:s.close()
async def current(c:HTTPAuthorizationCredentials=Depends(security)):return await get_current_user_from_token(c)
def org(u):
 if not u.get('organization'):raise HTTPException(403,'No active organization')
 return u['organization']['id']
def owned(x,u):
 if not x or x.invoice.organization_id!=org(u):raise HTTPException(404,'Payment attempt not found')
 return x
def write(s,fn):
 try:x=fn();s.commit();s.refresh(x);return x
 except HTTPException:s.rollback();raise
 except Exception:s.rollback();raise
def service(s):
 registry=PaymentProviderRegistry();registry.register(FakePaymentProvider())
 return PaymentProcessingService(s,registry)
def fail(fn):
 try:return fn()
 except (PaymentAttemptError,PaymentAttemptTransitionError) as e:raise HTTPException(409,str(e))
class AttemptCreate(BaseModel):
 provider:str;idempotency_key:str;amount:Decimal;currency:str
class AttemptOut(BaseModel):
 id:int;invoice_id:int;provider:str;status:str;amount:Decimal;currency:str;idempotency_key:str;provider_reference:str|None=None;version:int
 model_config=ConfigDict(from_attributes=True)
@router.post('/invoices/{invoice_id}/payment-attempts',response_model=AttemptOut,status_code=201)
def create(invoice_id:int,body:AttemptCreate,s:Session=Depends(get_session),u=Depends(current)):
 owned_invoice=SqlAlchemyInvoiceRepository(s).get_by_id(invoice_id)
 if not owned_invoice or owned_invoice.organization_id!=org(u):raise HTTPException(404,'Invoice not found')
 return write(s,lambda:fail(lambda:service(s).create_attempt(organization_id=org(u),invoice_id=invoice_id,**body.model_dump())))
@router.get('/payment-attempts/{attempt_id}',response_model=AttemptOut)
def get(attempt_id:int,s:Session=Depends(get_session),u=Depends(current)):
 return owned(SqlAlchemyPaymentAttemptRepository(s).get_by_id(attempt_id),u)
@router.post('/payment-attempts/{attempt_id}/reconcile',response_model=AttemptOut)
def reconcile(attempt_id:int,s:Session=Depends(get_session),u=Depends(current)):
 owned(SqlAlchemyPaymentAttemptRepository(s).get_by_id(attempt_id),u)
 return write(s,lambda:fail(lambda:service(s).reconcile(organization_id=org(u),attempt_id=attempt_id)))
