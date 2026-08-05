from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import delete, insert, select

from app.api.auth_routes import get_current_user_from_token
from app.db.database import SessionLocal
from app.db.intelligence_session_table import intelligence_session_table
from app.db.workspace_member_table import workspace_member_table
from app.db.workspace_table import workspace_table
from app.services.openai_service import generate_strategic_intelligence

router=APIRouter(prefix="/intelligence-sessions",tags=["Intelligence Sessions"])
security=HTTPBearer()

class CreateIntelligenceSessionRequest(BaseModel):
    # Retained for API compatibility; the authenticated identity is authoritative.
    organization_id:int|None=None
    workspace_id:int
    title:str
    goal:str
    domain:str="business"
    session_type:str="decision_analysis"

def clean_session(row):
    return {key:(value.isoformat() if key in {"created_at","updated_at"} and value else value) for key,value in row.items()}

def _identity_user_id(identity):
    user=identity.get("user") if identity else None
    user_id=user.get("id") if user else None
    if user_id is None: raise HTTPException(status_code=401,detail="Invalid authenticated identity")
    return user_id

def _identity_organization_id(identity):
    organization=identity.get("organization") if identity else None
    organization_id=organization.get("id") if organization else None
    if organization_id is None: raise HTTPException(status_code=404,detail="Workspace not found")
    return organization_id

def _owned_workspace(db,identity,workspace_id):
    organization_id=_identity_organization_id(identity);user_id=_identity_user_id(identity)
    workspace=db.execute(select(workspace_table).where(workspace_table.c.id==workspace_id,workspace_table.c.organization_id==organization_id,workspace_table.c.is_active==True)).mappings().first()
    if not workspace: raise HTTPException(status_code=404,detail="Workspace not found")
    membership=db.execute(select(workspace_member_table.c.id).where(workspace_member_table.c.workspace_id==workspace_id,workspace_member_table.c.user_id==user_id,workspace_member_table.c.is_active==True)).first()
    if not membership: raise HTTPException(status_code=404,detail="Workspace not found")
    return workspace

def _owned_session(db,identity,session_id):
    record=db.execute(select(intelligence_session_table).where(intelligence_session_table.c.id==session_id,intelligence_session_table.c.is_active==True)).mappings().first()
    if not record: raise HTTPException(status_code=404,detail="Session not found")
    _owned_workspace(db,identity,record["workspace_id"])
    return record

@router.post("")
async def create_intelligence_session(data:CreateIntelligenceSessionRequest,credentials:HTTPAuthorizationCredentials=Depends(security)):
    identity=await get_current_user_from_token(credentials);db=SessionLocal()
    try:
        workspace=_owned_workspace(db,identity,data.workspace_id);user_id=_identity_user_id(identity)
        summary=await generate_strategic_intelligence(data.goal)
        result=db.execute(insert(intelligence_session_table).values(organization_id=workspace["organization_id"],workspace_id=workspace["id"],created_by_user_id=user_id,title=data.title,goal=data.goal,domain=data.domain,session_type=data.session_type,status="completed",summary=summary,recommended_move="Execute focused strategic positioning before scaling operations.",risk_level="medium",business_model="ai_service_business",is_active=True))
        db.commit();record=db.execute(select(intelligence_session_table).where(intelligence_session_table.c.id==result.inserted_primary_key[0])).mappings().one()
        return {"success":True,"message":"Intelligence session generated successfully","session":clean_session(record)}
    except Exception:
        db.rollback();raise
    finally: db.close()

@router.get("/workspace/{workspace_id}")
async def list_workspace_sessions(workspace_id:int,credentials:HTTPAuthorizationCredentials=Depends(security)):
    identity=await get_current_user_from_token(credentials);db=SessionLocal()
    try:
        _owned_workspace(db,identity,workspace_id)
        records=db.execute(select(intelligence_session_table).where(intelligence_session_table.c.workspace_id==workspace_id,intelligence_session_table.c.is_active==True).order_by(intelligence_session_table.c.id.desc())).mappings().all()
        return {"success":True,"workspace_id":workspace_id,"sessions":[clean_session(record) for record in records]}
    finally: db.close()

@router.get("/{session_id}")
async def get_intelligence_session(session_id:int,credentials:HTTPAuthorizationCredentials=Depends(security)):
    identity=await get_current_user_from_token(credentials);db=SessionLocal()
    try: return {"success":True,"session":clean_session(_owned_session(db,identity,session_id))}
    finally: db.close()

@router.delete("/{session_id}")
async def delete_intelligence_session(session_id:int,credentials:HTTPAuthorizationCredentials=Depends(security)):
    identity=await get_current_user_from_token(credentials);db=SessionLocal()
    try:
        _owned_session(db,identity,session_id);db.execute(delete(intelligence_session_table).where(intelligence_session_table.c.id==session_id));db.commit()
        return {"success":True,"message":"Session deleted successfully"}
    except Exception:
        db.rollback();raise
    finally: db.close()
