from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session
from app.api.auth_routes import get_current_user_from_token
from app.commercial.billing import BillingAccountService, BillingError
from app.commercial.repositories import SqlAlchemyBillingAccountRepository
from app.db.database import SessionLocal

router=APIRouter(prefix="/commercial/billing-accounts",tags=["Commercial Billing Accounts"]);security=HTTPBearer()
def get_session():
 s=SessionLocal()
 try:yield s
 finally:s.close()
async def current(c:HTTPAuthorizationCredentials=Depends(security)):return await get_current_user_from_token(c)
def org(u):
 if not u.get("organization"):raise HTTPException(403,"No active organization")
 return u["organization"]["id"]
def owned(x,u):
 if not x or x.organization_id!=org(u):raise HTTPException(404,"Billing account not found")
 return x
def write(s,fn):
 try:x=fn();s.commit();s.refresh(x);return x
 except HTTPException:s.rollback();raise
 except Exception:s.rollback();raise
def domain(fn):
 try:return fn()
 except BillingError as exc:raise HTTPException(409,"Billing account operation rejected") from exc
class BillingAccountCreate(BaseModel):
 model_config=ConfigDict(extra="ignore")
 organization_id:int|None=None;billing_email:str;billing_name:str;country_code:str;currency:str
 company_name:str|None=None;address_line_1:str|None=None;address_line_2:str|None=None;city:str|None=None;region:str|None=None;postal_code:str|None=None;tax_identifier:str|None=None
class BillingAccountUpdate(BaseModel):
 model_config=ConfigDict(extra="ignore")
 organization_id:int|None=None;billing_email:str|None=None;billing_name:str|None=None;country_code:str|None=None;currency:str|None=None
 company_name:str|None=None;address_line_1:str|None=None;address_line_2:str|None=None;city:str|None=None;region:str|None=None;postal_code:str|None=None;tax_identifier:str|None=None
class BillingAccountOut(BaseModel):
 model_config=ConfigDict(from_attributes=True)
 id:int;organization_id:int;billing_email:str;billing_name:str;country_code:str;currency:str;billing_status:str;version:int
 company_name:str|None=None;address_line_1:str|None=None;city:str|None=None;tax_identifier:str|None=None
@router.get("",response_model=list[BillingAccountOut])
def list_accounts(s:Session=Depends(get_session),u=Depends(current)):
 x=SqlAlchemyBillingAccountRepository(s).get_by_organization_id(org(u));return [x] if x else []
@router.get("/{account_id}",response_model=BillingAccountOut)
def get_account(account_id:int,s:Session=Depends(get_session),u=Depends(current)):return owned(SqlAlchemyBillingAccountRepository(s).get_by_id(account_id),u)
@router.post("",status_code=201,response_model=BillingAccountOut)
def create(body:BillingAccountCreate,s:Session=Depends(get_session),u=Depends(current)):
 d=body.model_dump();d["organization_id"]=org(u);return write(s,lambda:domain(lambda:BillingAccountService(s).create_billing_account(**d)))
@router.patch("/{account_id}",response_model=BillingAccountOut)
def update(account_id:int,body:BillingAccountUpdate,s:Session=Depends(get_session),u=Depends(current)):
 owned(SqlAlchemyBillingAccountRepository(s).get_by_id(account_id),u);d={k:v for k,v in body.model_dump().items() if k!="organization_id" and v is not None};return write(s,lambda:domain(lambda:BillingAccountService(s).update_billing_details(account_id,**d)))
def status(account_id,status,s,u):
 owned(SqlAlchemyBillingAccountRepository(s).get_by_id(account_id),u);return write(s,lambda:domain(lambda:BillingAccountService(s).change_billing_status(account_id,status)))
@router.post("/{account_id}/activate",response_model=BillingAccountOut)
def activate(account_id:int,s:Session=Depends(get_session),u=Depends(current)):return status(account_id,"active",s,u)
@router.post("/{account_id}/suspend",response_model=BillingAccountOut)
def suspend(account_id:int,s:Session=Depends(get_session),u=Depends(current)):return status(account_id,"suspended",s,u)
@router.post("/{account_id}/close",response_model=BillingAccountOut)
def close(account_id:int,s:Session=Depends(get_session),u=Depends(current)):return status(account_id,"closed",s,u)
