from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy import select, insert

from app.db.database import database
from app.db.organization_table import organization_table
from app.db.workspace_table import workspace_table
from app.db.intelligence_session_table import intelligence_session_table
from app.api.auth_routes import get_current_user_from_token
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


router = APIRouter(prefix="/intelligence-sessions", tags=["Intelligence Sessions"])
security = HTTPBearer()


class CreateIntelligenceSessionRequest(BaseModel):
    organization_id: int
    workspace_id: int
    title: str
    goal: str
    domain: str = "business"
    session_type: str = "decision_analysis"
    summary: str | None = None
    recommended_move: str | None = None
    risk_level: str | None = None
    business_model: str | None = None


def clean_session(row):
    return {
        "id": row["id"],
        "organization_id": row["organization_id"],
        "workspace_id": row["workspace_id"],
        "created_by_user_id": row["created_by_user_id"],
        "title": row["title"],
        "goal": row["goal"],
        "domain": row["domain"],
        "session_type": row["session_type"],
        "status": row["status"],
        "summary": row["summary"],
        "recommended_move": row["recommended_move"],
        "risk_level": row["risk_level"],
        "business_model": row["business_model"],
        "is_active": row["is_active"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
    }


async def verify_workspace_access(user_id: int, organization_id: int, workspace_id: int):
    org = await database.fetch_one(
        select(organization_table).where(
            organization_table.c.id == organization_id
        )
    )

    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    if org["owner_user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Not allowed for this organization")

    workspace = await database.fetch_one(
        select(workspace_table).where(
            workspace_table.c.id == workspace_id
        )
    )

    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    if workspace["organization_id"] != organization_id:
        raise HTTPException(
            status_code=400,
            detail="Workspace does not belong to this organization"
        )

    return org, workspace


@router.post("")
async def create_intelligence_session(
    data: CreateIntelligenceSessionRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    user = await get_current_user_from_token(credentials)

    await verify_workspace_access(
        user_id=user["id"],
        organization_id=data.organization_id,
        workspace_id=data.workspace_id
    )

    query = insert(intelligence_session_table).values(
        organization_id=data.organization_id,
        workspace_id=data.workspace_id,
        created_by_user_id=user["id"],
        title=data.title,
        goal=data.goal,
        domain=data.domain,
        session_type=data.session_type,
        status="completed",
        summary=data.summary,
        recommended_move=data.recommended_move,
        risk_level=data.risk_level,
        business_model=data.business_model,
        is_active=True,
    )

    session_id = await database.execute(query)

    session = await database.fetch_one(
        select(intelligence_session_table).where(
            intelligence_session_table.c.id == session_id
        )
    )

    return {
        "success": True,
        "message": "Intelligence session saved successfully",
        "session": clean_session(session),
    }


from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()


@router.get("/workspace/{workspace_id}")
async def list_workspace_sessions(
    workspace_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    user = await get_current_user_from_token(credentials)

    workspace = await database.fetch_one(
        select(workspace_table).where(workspace_table.c.id == workspace_id)
    )

    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    org = await database.fetch_one(
        select(organization_table).where(
            organization_table.c.id == workspace["organization_id"]
        )
    )

    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    if org["owner_user_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Not allowed")

    query = (
        select(intelligence_session_table)
        .where(intelligence_session_table.c.workspace_id == workspace_id)
        .where(intelligence_session_table.c.is_active == True)
        .order_by(intelligence_session_table.c.id.desc())
    )

    rows = await database.fetch_all(query)

    return {
        "success": True,
        "workspace_id": workspace_id,
        "sessions": [clean_session(row) for row in rows],
    }


@router.get("/{session_id}")
async def get_intelligence_session(
    session_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    user = await get_current_user_from_token(credentials)

    session = await database.fetch_one(
        select(intelligence_session_table).where(
            intelligence_session_table.c.id == session_id
        )
    )

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    org = await database.fetch_one(
        select(organization_table).where(
            organization_table.c.id == session["organization_id"]
        )
    )

    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    if org["owner_user_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Not allowed")

    return {
        "success": True,
        "session": clean_session(session),
    }