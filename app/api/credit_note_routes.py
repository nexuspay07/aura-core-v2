from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter,Depends,HTTPException
from fastapi.security import HTTPAuthorizationCredentials,HTTPBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.api.auth_routes import get_current_user_from_token
from app.commercial.credit_note_service import CreditNoteService
from app.commercial.repositories import SqlAlchemyCreditNoteRepository
from app.commercial.billing import BillingError,BillingPersistenceConflictError

router=APIRouter(prefix='/commercial/credit-notes',tags=['Commercial Credit Notes']);security=HTTPBearer()
def get_session():
 s=SessionLocal()
 try:yield s
 finally:s.close()
async def current(credentials:HTTPAuthorizationCredentials=Depends(security)):return await get_current_user_from_token(credentials)
def org(user):
 if not user.get('organization'):raise HTTPException(403,'No active organization')
 return user['organization']['id']
def owned(x,user):
 if not x or x.organization_id!=org(user):raise HTTPException(404,'Credit note not found')
 return x
def write(s,fn):
 try:x=fn();s.commit();s.refresh(x);return x
 except HTTPException:s.rollback();raise
 except Exception:s.rollback();raise
class CreditNoteCreate(BaseModel):
 organization_id:int|None=None;invoice_id:int;credit_note_number:str;currency:str;reason:str|None=None
class CreditNoteUpdate(BaseModel):reason:str|None=None
class CreditNoteOut(BaseModel):
 id:int;organization_id:int;invoice_id:int;credit_note_number:str;status:str;currency:str;subtotal:Decimal;tax:Decimal;total:Decimal;amount_applied:Decimal;amount_remaining:Decimal;version:int
 class Config:from_attributes=True
def fail(fn):
 try:return fn()
 except BillingPersistenceConflictError:raise HTTPException(409,'Credit note conflict')
 except BillingError:raise HTTPException(409,'Credit note operation rejected')
@router.get('',response_model=list[CreditNoteOut])
def list_notes(s:Session=Depends(get_session),user=Depends(current)):return SqlAlchemyCreditNoteRepository(s).list_by_organization(org(user))
@router.get('/{credit_note_id}',response_model=CreditNoteOut)
def get_note(credit_note_id:int,s:Session=Depends(get_session),user=Depends(current)):return owned(SqlAlchemyCreditNoteRepository(s).get_by_id(credit_note_id),user)
@router.post('',status_code=201,response_model=CreditNoteOut)
def create_note(body:CreditNoteCreate,s:Session=Depends(get_session),user=Depends(current)):
 d=body.model_dump();d['organization_id']=org(user);return write(s,lambda:fail(lambda:CreditNoteService(s).create_draft(**d)))
@router.patch('/{credit_note_id}',response_model=CreditNoteOut)
def update_note(credit_note_id:int,body:CreditNoteUpdate,s:Session=Depends(get_session),user=Depends(current)):
 x=owned(SqlAlchemyCreditNoteRepository(s).get_by_id(credit_note_id),user)
 if x.status!='draft':raise HTTPException(409,'Credit note operation rejected')
 if body.reason is not None:x.reason=body.reason
 return write(s,lambda:x)
@router.post('/{credit_note_id}/issue',response_model=CreditNoteOut)
def issue_note(credit_note_id:int,s:Session=Depends(get_session),user=Depends(current)):
 owned(SqlAlchemyCreditNoteRepository(s).get_by_id(credit_note_id),user);return write(s,lambda:fail(lambda:CreditNoteService(s).issue_credit_note(credit_note_id)))
@router.post('/{credit_note_id}/void',response_model=CreditNoteOut)
def void_note(credit_note_id:int,s:Session=Depends(get_session),user=Depends(current)):
 owned(SqlAlchemyCreditNoteRepository(s).get_by_id(credit_note_id),user);return write(s,lambda:fail(lambda:CreditNoteService(s).void_credit_note(credit_note_id)))
