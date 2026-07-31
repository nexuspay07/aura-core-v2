from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from calendar import monthrange
import re
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.commercial.models import BillingAccount, Subscription
from app.db.organization_orm import Organization

class BillingError(Exception): pass
class BillingAccountNotFoundError(BillingError): pass
class BillingAccountAlreadyExistsError(BillingError): pass
class InvalidBillingEmailError(BillingError): pass
class InvalidBillingNameError(BillingError): pass
class InvalidCountryCodeError(BillingError): pass
class InvalidCurrencyError(BillingError): pass
class InvalidBillingStatusError(BillingError): pass
class InvalidBillingStatusTransitionError(BillingError): pass
class BillingPersistenceConflictError(BillingError): pass
class UnsupportedBillingCycleError(BillingError): pass
class InvalidBillingPeriodError(BillingError): pass
class MissingBillingAnchorError(BillingError): pass

class BillingAccountService:
 def __init__(self,session:Session,clock=lambda:datetime.now(timezone.utc)):
  from app.commercial.repositories import SqlAlchemyBillingAccountRepository
  self.session=session;self.repo=SqlAlchemyBillingAccountRepository(session);self.clock=clock
 def _validate(self,v):
  v["billing_email"]=v["billing_email"].strip();v["billing_name"]=v["billing_name"].strip()
  if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$",v["billing_email"]):raise InvalidBillingEmailError()
  if not v["billing_name"]:raise InvalidBillingNameError()
  if not re.match(r"^[A-Z]{2}$",v["country_code"]):raise InvalidCountryCodeError()
  if not re.match(r"^[A-Z]{3}$",v["currency"]):raise InvalidCurrencyError()
 def create_billing_account(self,**v):
  if self.session.get(Organization,v["organization_id"]) is None: raise BillingAccountNotFoundError()
  if self.repo.get_by_organization_id(v["organization_id"]): raise BillingAccountAlreadyExistsError()
  self._validate(v);now=self.clock();v.setdefault("billing_status","active");v.setdefault("version",1);v["created_at"]=now;v["updated_at"]=now
  try:return self.repo.save(BillingAccount(**v))
  except Exception as e:self.session.rollback();raise BillingPersistenceConflictError() from e
 def update_billing_details(self,account_id,**v):
  a=self.repo.get_by_id(account_id)
  if not a: raise BillingAccountNotFoundError()
  allowed={"billing_email","billing_name","company_name","address_line_1","address_line_2","city","region","postal_code","country_code","currency","tax_identifier"}; v={k:x for k,x in v.items() if k in allowed}; merged={"billing_email":v.get("billing_email",a.billing_email),"billing_name":v.get("billing_name",a.billing_name),"country_code":v.get("country_code",a.country_code),"currency":v.get("currency",a.currency)};self._validate(merged)
  for k,x in v.items():setattr(a,k,merged[k] if k in merged else x)
  a.version+=1;a.updated_at=self.clock()
  try:return self.repo.save(a)
  except Exception as e:self.session.rollback();raise BillingPersistenceConflictError() from e
 def change_billing_status(self,account_id,status):
  a=self.repo.get_by_id(account_id)
  if not a: raise BillingAccountNotFoundError()
  if status not in {"active","suspended","closed"}:raise InvalidBillingStatusError()
  if status==a.billing_status or (a.billing_status,status) not in {("active","suspended"),("active","closed"),("suspended","active"),("suspended","closed")}:raise InvalidBillingStatusTransitionError()
  a.billing_status=status;a.version+=1;a.updated_at=self.clock()
  try:return self.repo.save(a)
  except Exception as e:self.session.rollback();raise BillingPersistenceConflictError() from e
@dataclass(frozen=True)
class BillingPeriod:
 period_start:datetime;period_end:datetime;billing_cycle:str;anchor_day:int;timezone_name:str="UTC"
 def __post_init__(self):
  if self.timezone_name!="UTC" or self.period_start.tzinfo is None or self.period_end.tzinfo is None or self.period_end<=self.period_start or self.billing_cycle=="monthly" and not 1<=self.anchor_day<=31:raise InvalidBillingPeriodError()
  object.__setattr__(self,"period_start",self.period_start.astimezone(timezone.utc));object.__setattr__(self,"period_end",self.period_end.astimezone(timezone.utc))
class BillingPeriodCalculator:
 @staticmethod
 def _anchor(y,m,d): return datetime(y,m,min(d,monthrange(y,m)[1]),tzinfo=timezone.utc)
 @classmethod
 def calculate_current_period(cls,subscription,reference_time,anchor_day=None):
  if subscription.billing_cycle=="custom":raise UnsupportedBillingCycleError()
  if subscription.billing_cycle not in {"monthly","annual"}: raise UnsupportedBillingCycleError()
  if reference_time.tzinfo is None:raise InvalidBillingPeriodError()
  anchor=anchor_day or getattr(subscription,"starts_at",None)
  if anchor is None:raise MissingBillingAnchorError()
  a=anchor_day or anchor.day; r=reference_time.astimezone(timezone.utc)
  if subscription.billing_cycle=="monthly":
   start=cls._anchor(r.year,r.month,a)
   if r<start: y,m=(r.year-1,12) if r.month==1 else (r.year,r.month-1);start=cls._anchor(y,m,a)
   y,m=(start.year+1,1) if start.month==12 else (start.year,start.month+1);end=cls._anchor(y,m,a)
  else:
   start=cls._anchor(r.year,subscription.starts_at.month,a)
   if r<start:start=cls._anchor(r.year-1,subscription.starts_at.month,a)
   end=cls._anchor(start.year+1,subscription.starts_at.month,a)
  return BillingPeriod(start,end,subscription.billing_cycle,a)
 @classmethod
 def calculate_next_period(cls,subscription,reference_time,anchor_day=None):
  p=cls.calculate_current_period(subscription,reference_time,anchor_day);return cls.calculate_current_period(subscription,p.period_end,anchor_day)
 @classmethod
 def calculate_previous_period(cls,subscription,reference_time,anchor_day=None):
  p=cls.calculate_current_period(subscription,reference_time,anchor_day);return cls.calculate_current_period(subscription,p.period_start.replace(microsecond=0)-__import__('datetime').timedelta(seconds=1),anchor_day)
 calculate_period_for_timestamp=calculate_current_period
