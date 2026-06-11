from fastapi import (
    APIRouter,
    HTTPException,
    Depends
)

from fastapi.security import (
    HTTPBearer,
    HTTPAuthorizationCredentials
)

from pydantic import BaseModel
from sqlalchemy import delete


from sqlalchemy import (
    select,
    insert
)

from app.db.database import SessionLocal

from app.db.organization_table import (
    organization_table
)

from app.db.workspace_table import (
    workspace_table
)

from app.db.intelligence_session_table import (
    intelligence_session_table
)

from app.api.auth_routes import (
    get_current_user_from_token
)

from app.services.openai_service import (
    generate_strategic_intelligence
)




router = APIRouter(
    prefix="/intelligence-sessions",
    tags=["Intelligence Sessions"]
)

security = HTTPBearer()


# =====================================================
# REQUEST MODEL
# =====================================================

class CreateIntelligenceSessionRequest(
    BaseModel
):

    organization_id: int

    workspace_id: int

    title: str

    goal: str

    domain: str = "business"

    session_type: str = (
        "decision_analysis"
    )


# =====================================================
# CLEAN SESSION
# =====================================================

def clean_session(row):

    return {
        "id": row["id"],
        "organization_id": (
            row["organization_id"]
        ),
        "workspace_id": (
            row["workspace_id"]
        ),
        "created_by_user_id": (
            row["created_by_user_id"]
        ),
        "title": row["title"],
        "goal": row["goal"],
        "domain": row["domain"],
        "session_type": (
            row["session_type"]
        ),
        "status": row["status"],
        "summary": row["summary"],
        "recommended_move": (
            row["recommended_move"]
        ),
        "risk_level": (
            row["risk_level"]
        ),
        "business_model": (
            row["business_model"]
        ),
        "is_active": (
            row["is_active"]
        ),
        "created_at": (
            row["created_at"].isoformat()
            if row["created_at"]
            else None
        ),
        "updated_at": (
            row["updated_at"].isoformat()
            if row["updated_at"]
            else None
        ),
    }


# =====================================================
# VERIFY WORKSPACE ACCESS
# =====================================================

async def verify_workspace_access(
    user_id: int,
    organization_id: int,
    workspace_id: int
):

    db = SessionLocal()

    try:

        org_result = db.execute(
            select(organization_table)
            .where(
                organization_table.c.id
                == organization_id
            )
        )

        org = org_result.fetchone()

        if not org:

            raise HTTPException(
                status_code=404,
                detail=(
                    "Organization not found"
                )
            )

        org_data = dict(org._mapping)

        if (
            org_data["owner_user_id"]
            != user_id
        ):

            raise HTTPException(
                status_code=403,
                detail=(
                    "Not allowed for this "
                    "organization"
                )
            )

        workspace_result = db.execute(
            select(workspace_table)
            .where(
                workspace_table.c.id
                == workspace_id
            )
        )

        workspace = (
            workspace_result.fetchone()
        )

        if not workspace:

            raise HTTPException(
                status_code=404,
                detail=(
                    "Workspace not found"
                )
            )

        workspace_data = dict(
            workspace._mapping
        )

        if (
            workspace_data[
                "organization_id"
            ]
            != organization_id
        ):

            raise HTTPException(
                status_code=400,
                detail=(
                    "Workspace does not belong "
                    "to this organization"
                )
            )

        return (
            org_data,
            workspace_data
        )

    finally:

        db.close()


# =====================================================
# CREATE INTELLIGENCE SESSION
# =====================================================

@router.post("")
async def create_intelligence_session(
    data: CreateIntelligenceSessionRequest,
    credentials:
    HTTPAuthorizationCredentials = Depends(
        security
    )
):

    user = (
        await get_current_user_from_token(
            credentials
        )
    )

    await verify_workspace_access(
        user_id=user["id"],
        organization_id=(
            data.organization_id
        ),
        workspace_id=data.workspace_id
    )

    

    # =====================================================
    # REAL AI STRATEGIC INTELLIGENCE
    # =====================================================

    summary = (
        await generate_strategic_intelligence(
            data.goal
        )
    )

    recommended_move = (
        "Execute focused strategic "
        "positioning before scaling "
        "operations."
    )

    risk_level = "medium"

    business_model = (
        "ai_service_business"
    )

    db = SessionLocal()

    try:

        # =====================================================
        # SAVE SESSION
        # =====================================================

        query = insert(
            intelligence_session_table
        ).values(
            organization_id=(
                data.organization_id
            ),
            workspace_id=(
                data.workspace_id
            ),
            created_by_user_id=(
                user["id"]
            ),
            title=data.title,
            goal=data.goal,
            domain=data.domain,
            session_type=(
                data.session_type
            ),
            status="completed",
            summary=summary,
            recommended_move=(
                recommended_move
            ),
            risk_level=risk_level,
            business_model=(
                business_model
            ),
            is_active=True,
        )

        result = db.execute(query)

        db.commit()

        session_id = (
            result.inserted_primary_key[0]
        )

        session_result = db.execute(
            select(
                intelligence_session_table
            ).where(
                intelligence_session_table.c.id
                == session_id
            )
        )

        session = (
            session_result.fetchone()
        )

    finally:

        db.close()

    return {
        "success": True,
        "message": (
            "Intelligence session generated "
            "successfully"
        ),
        "session": clean_session(
            dict(session._mapping)
        ),
    }


# =====================================================
# LIST WORKSPACE SESSIONS
# =====================================================

@router.get("/workspace/{workspace_id}")
async def list_workspace_sessions(
    workspace_id: int,
    credentials:
    HTTPAuthorizationCredentials = Depends(
        security
    )
):

    user = (
        await get_current_user_from_token(
            credentials
        )
    )

    db = SessionLocal()

    try:

        workspace_result = db.execute(
            select(workspace_table)
            .where(
                workspace_table.c.id
                == workspace_id
            )
        )

        workspace = (
            workspace_result.fetchone()
        )

        if not workspace:

            raise HTTPException(
                status_code=404,
                detail=(
                    "Workspace not found"
                )
            )

        workspace_data = dict(
            workspace._mapping
        )

        org_result = db.execute(
            select(organization_table)
            .where(
                organization_table.c.id
                == workspace_data[
                    "organization_id"
                ]
            )
        )

        org = org_result.fetchone()

        if not org:

            raise HTTPException(
                status_code=404,
                detail=(
                    "Organization not found"
                )
            )

        org_data = dict(org._mapping)

        if (
            org_data["owner_user_id"]
            != user["id"]
        ):

            raise HTTPException(
                status_code=403,
                detail="Not allowed"
            )

        query = (
            select(
                intelligence_session_table
            )
            .where(
                intelligence_session_table
                .c.workspace_id
                == workspace_id
            )
            .where(
                intelligence_session_table
                .c.is_active == True
            )
            .order_by(
                intelligence_session_table
                .c.id.desc()
            )
        )

        result = db.execute(query)

        rows = result.fetchall()

    finally:

        db.close()

    return {
        "success": True,
        "workspace_id": workspace_id,
        "sessions": [
            clean_session(
                dict(row._mapping)
            )
            for row in rows
        ],
    }


# =====================================================
# GET SINGLE SESSION
# =====================================================

@router.get("/{session_id}")
async def get_intelligence_session(
    session_id: int,
    credentials:
    HTTPAuthorizationCredentials = Depends(
        security
    )
):

    user = (
        await get_current_user_from_token(
            credentials
        )
    )

    db = SessionLocal()

    try:

        session_result = db.execute(
            select(
                intelligence_session_table
            ).where(
                intelligence_session_table.c.id
                == session_id
            )
        )

        session = (
            session_result.fetchone()
        )

        if not session:

            raise HTTPException(
                status_code=404,
                detail="Session not found"
            )

        session_data = dict(
            session._mapping
        )

        org_result = db.execute(
            select(organization_table)
            .where(
                organization_table.c.id
                == session_data[
                    "organization_id"
                ]
            )
        )

        org = org_result.fetchone()

        if not org:

            raise HTTPException(
                status_code=404,
                detail=(
                    "Organization not found"
                )
            )

        org_data = dict(org._mapping)

        if (
            org_data["owner_user_id"]
            != user["id"]
        ):

            raise HTTPException(
                status_code=403,
                detail="Not allowed"
            )

    finally:

        db.close()

    return {
        "success": True,
        "session": clean_session(
            session_data
        ),
    }

# =====================================================
# DELETE SESSION
# =====================================================

@router.delete("/{session_id}")
async def delete_intelligence_session(
    session_id: int,
    credentials:
    HTTPAuthorizationCredentials = Depends(
        security
    )
):

    user = (
        await get_current_user_from_token(
            credentials
        )
    )

    db = SessionLocal()

    try:

        # -------------------------------------
        # VERIFY SESSION EXISTS
        # -------------------------------------

        session_result = db.execute(
            select(
                intelligence_session_table
            ).where(
                intelligence_session_table.c.id
                == session_id
            )
        )

        session = (
            session_result.fetchone()
        )

        if not session:

            raise HTTPException(
                status_code=404,
                detail="Session not found"
            )

        session_data = dict(
            session._mapping
        )

        # -------------------------------------
        # VERIFY USER OWNS ORGANIZATION
        # -------------------------------------

        org_result = db.execute(
            select(
                organization_table
            ).where(
                organization_table.c.id
                == session_data[
                    "organization_id"
                ]
            )
        )

        org = org_result.fetchone()

        if not org:

            raise HTTPException(
                status_code=404,
                detail="Organization not found"
            )

        org_data = dict(
            org._mapping
        )

        if (
            org_data["owner_user_id"]
            != user["id"]
        ):

            raise HTTPException(
                status_code=403,
                detail="Not allowed"
            )

        # -------------------------------------
        # DELETE SESSION
        # -------------------------------------

        query = delete(
            intelligence_session_table
        ).where(
            intelligence_session_table.c.id
            == session_id
        )

        db.execute(query)

        db.commit()

    finally:

        db.close()

    return {
        "success": True,
        "message":
        "Session deleted successfully"
    }