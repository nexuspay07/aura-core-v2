"""Server-side authorization for platform-wide Control Center access."""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.api.auth_routes import get_current_user_from_token

security = HTTPBearer()

async def require_platform_admin(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    identity = await get_current_user_from_token(credentials)
    user = identity.get("user") if identity else None
    if not user or user.get("role") != "platform_admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return identity
