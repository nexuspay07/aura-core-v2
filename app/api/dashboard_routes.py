from fastapi import (
    APIRouter,
    Depends,
    HTTPException
)

from app.db.database import SessionLocal

from app.services.dashboard_service import (
    dashboard_service
)

from app.api.auth_routes import (
    get_current_user_from_token
)

from fastapi.security import (
    HTTPBearer,
    HTTPAuthorizationCredentials
)


router = APIRouter(

    prefix="/dashboard",

    tags=["Dashboard"]

)

security = HTTPBearer()


@router.get("/")
async def get_dashboard(

    credentials: HTTPAuthorizationCredentials = Depends(
        security
    )

):

    user = await get_current_user_from_token(
        credentials
    )

    db = SessionLocal()

    try:

        organization_id = (

    user["organization"]["id"]

)

        workspace_id = (

    user["workspace"]["id"]

)

        if organization_id is None:

            raise HTTPException(

                status_code=400,

                detail="User does not belong to an organization."

            )

        if workspace_id is None:

            raise HTTPException(

                status_code=400,

                detail="User does not belong to a workspace."

            )

        dashboard = (

            await dashboard_service.build_dashboard(

                db=db,

                organization_id=organization_id,

                workspace_id=workspace_id,

                user=user

            )

        )

        return {

            "success": True,

            "dashboard": dashboard

        }

    finally:

        db.close()
