from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.services.chat_service import chat_service
from app.api.auth_routes import get_current_user_from_token

router = APIRouter()
security = HTTPBearer()


# ==========================================
# REQUEST MODEL
# ==========================================

class ConversationRequest(BaseModel):
    message: str
    session_id: int | None = None
    organization_id: int | None = None
    workspace_id: int | None = None


# ==========================================
# CHAT ROUTE
# ==========================================

@router.post("/chat")
async def chat(
    data: ConversationRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
):

    identity = await get_current_user_from_token(credentials)
    organization = identity.get("organization")
    workspace = identity.get("workspace")
    if not organization or not workspace:
        from fastapi import HTTPException
        raise HTTPException(status_code=409, detail="Complete organization onboarding before using chat.")

    if data.organization_id not in (None, organization["id"]) or data.workspace_id not in (None, workspace["id"]):
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="The requested tenant context is not authorized.")

    return await chat_service.process_chat(

        message=data.message,

        session_id=data.session_id,

        organization_id=organization["id"],
        workspace_id=workspace["id"],
        user=identity["user"],

    )
