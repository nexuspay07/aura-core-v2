"""Read-only, platform-admin Control Center API."""
from fastapi import APIRouter, Depends, Query

from app.auth.platform_admin import require_platform_admin
from app.db.database import SessionLocal
from app.schemas.control_center import IntelligenceResponse, OverviewResponse, UsersResponse
from app.services import control_center_service


router = APIRouter(prefix="/admin/control-center", tags=["Control Center"], dependencies=[Depends(require_platform_admin)])


@router.get("/overview", response_model=OverviewResponse)
def overview(window: str = Query("7d")):
    start, end = control_center_service.resolve_window(window)
    with SessionLocal() as db:
        return control_center_service.overview(db, start, end)


@router.get("/users", response_model=UsersResponse)
def users(window: str = Query("30d"), page_size: int = Query(25, ge=1, le=100), cursor: str | None = None):
    start, end = control_center_service.resolve_window(window)
    with SessionLocal() as db:
        return control_center_service.users(db, start, end, page_size, cursor)


@router.get("/intelligence", response_model=IntelligenceResponse)
def intelligence(window: str = Query("7d")):
    start, end = control_center_service.resolve_window(window)
    with SessionLocal() as db:
        return control_center_service.intelligence(db, start, end, window)
