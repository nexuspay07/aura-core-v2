from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter,Depends,HTTPException
from fastapi.security import HTTPBearer,HTTPAuthorizationCredentials
from pydantic import BaseModel,ConfigDict
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.api.auth_routes import get_current_user_from_token
from app.commercial.refund_service import RefundService
from app.commercial.repositories import SqlAlchemyRefundRepository
from app.commercial.billing import BillingError,BillingPersistenceConflictError
router=APIRouter(prefix='/commercial/refunds',tags=['Commercial Refunds']);security=HTTPBearer()
def get_session():
 s=SessionLocal()
 try:yield s
 finally:s.close()
async def current(c:HTTPAuthorizationCredentials=Depends(security)):return await get_current_user_from_token(c)
def org(u):
 if not u.get('organization'):raise HTTPException(403,'No active organization')
 return u['organization']['id']
def owned(x,u):
 if not x or x.organization_id!=org(u):raise HTTPException(404,'Refund not found')
 return x
def write(s,fn):
 try:x=fn();s.commit();s.refresh(x);return x
 except HTTPException:s.rollback();raise
 except Exception:s.rollback();raise
class RefundCreate(BaseModel):
 organization_id:int|None=None;invoice_id:int;payment_attempt_id:int;amount:Decimal;currency:str;idempotency_key:str;provider:str;refund_number:str;reason:str|None=None;provider_reference:str|None=None;credit_note_id:int|None=None
class RefundOut(BaseModel):
 id:int;organization_id:int;invoice_id:int;payment_attempt_id:int;refund_number:str;status:str;amount:Decimal;currency:str;idempotency_key:str;provider:str;version:int
 model_config=ConfigDict(from_attributes=True)
class Action(BaseModel):expected_version:int;provider_reference:str|None=None;failure_code:str|None=None;failure_message:str|None=None
def fail(fn):
 try:return fn()
 except BillingPersistenceConflictError:raise HTTPException(409,'Refund conflict')
 except BillingError:raise HTTPException(409,'Refund operation rejected')
@router.get('',response_model=list[RefundOut])
def list_refunds(s:Session=Depends(get_session),u=Depends(current)):return SqlAlchemyRefundRepository(s).list_by_organization(org(u))
@router.get('/{refund_id}',response_model=RefundOut)
def get_refund(refund_id:int,s:Session=Depends(get_session),u=Depends(current)):return owned(SqlAlchemyRefundRepository(s).get_by_id(refund_id),u)
@router.post('',status_code=201,response_model=RefundOut)
def create(body:RefundCreate,s:Session=Depends(get_session),u=Depends(current)):
 d=body.model_dump();d['organization_id']=org(u);return write(s,lambda:fail(lambda:RefundService(s).create_refund(**d)))
def action(refund_id:int,body:Action,s:Session,u,method):
 owned(SqlAlchemyRefundRepository(s).get_by_id(refund_id),u)
 fields={"mark_processing":{"provider_reference"},"mark_succeeded":{"provider_reference"},"mark_failed":{"failure_code","failure_message"},"cancel_refund":set()}[method]
 values={key:value for key,value in body.model_dump(exclude={"expected_version"}).items() if key in fields and value is not None}
 return write(s,lambda:fail(lambda:getattr(RefundService(s),method)(refund_id,organization_id=org(u),expected_version=body.expected_version,**values)))
@router.post('/{refund_id}/processing',response_model=RefundOut)
def processing(refund_id:int,body:Action,s:Session=Depends(get_session),u=Depends(current)):return action(refund_id,body,s,u,'mark_processing')
@router.post('/{refund_id}/succeeded',response_model=RefundOut)
def succeeded(refund_id:int,body:Action,s:Session=Depends(get_session),u=Depends(current)):return action(refund_id,body,s,u,'mark_succeeded')
@router.post('/{refund_id}/failed',response_model=RefundOut)
def failed(refund_id:int,body:Action,s:Session=Depends(get_session),u=Depends(current)):return action(refund_id,body,s,u,'mark_failed')
@router.post('/{refund_id}/cancel',response_model=RefundOut)
def cancel(refund_id:int,body:Action,s:Session=Depends(get_session),u=Depends(current)):return action(refund_id,body,s,u,'cancel_refund')
