from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter,Depends,HTTPException
from fastapi.security import HTTPBearer,HTTPAuthorizationCredentials
from pydantic import BaseModel,ConfigDict
from sqlalchemy.orm import Session
from app.api.auth_routes import get_current_user_from_token
from app.commercial.metering import UsageMeteringService,UsageMeteringError
from app.commercial.repositories import SqlAlchemyUsageRecordRepository
from app.db.database import SessionLocal
router=APIRouter(prefix="/commercial/usage",tags=["Commercial Usage"]);security=HTTPBearer()
def get_session():
 s=SessionLocal()
 try:yield s
 finally:s.close()
async def current(c:HTTPAuthorizationCredentials=Depends(security)):return await get_current_user_from_token(c)
def org(u):
 if not u.get("organization"):raise HTTPException(403,"No active organization")
 return u["organization"]["id"]
def owned(x,u):
 if not x or x.organization_id!=org(u):raise HTTPException(404,"Usage record not found")
 return x
def write(s,fn):
 try:x=fn();s.commit();s.refresh(x);return x
 except Exception:s.rollback();raise
def domain(fn):
 try:return fn()
 except UsageMeteringError as e:raise HTTPException(409,"Usage operation rejected") from e
class UsageCreate(BaseModel):
 model_config=ConfigDict(extra="ignore")
 organization_id:int|None=None;feature_key:str;quantity:Decimal;unit:str;occurred_at:datetime;idempotency_key:str|None=None;source_type:str|None=None;source_id:str|None=None;period_start:datetime|None=None;period_end:datetime|None=None
class UsageOut(BaseModel):
 model_config=ConfigDict(from_attributes=True)
 id:int;organization_id:int;subscription_id:int;feature_key:str;quantity:Decimal;unit:str;occurred_at:datetime;idempotency_key:str|None=None
@router.get("",response_model=list[UsageOut])
def list_usage(s:Session=Depends(get_session),u=Depends(current)):return SqlAlchemyUsageRecordRepository(s).list_for_organization(org(u))
@router.get("/{record_id}",response_model=UsageOut)
def get_usage(record_id:int,s:Session=Depends(get_session),u=Depends(current)):return owned(SqlAlchemyUsageRecordRepository(s).get_by_id(record_id),u)
@router.post("",status_code=201,response_model=UsageOut)
def record(body:UsageCreate,s:Session=Depends(get_session),u=Depends(current)):
 d=body.model_dump();d["organization_id"]=org(u);return write(s,lambda:domain(lambda:UsageMeteringService(s).record_usage(**d)))
