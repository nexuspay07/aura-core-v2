from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.db.database import SessionLocal
from app.db.strategy import strategies
from app.api.auth_routes import get_current_user_from_token
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

router = APIRouter(
    prefix="/marketplace",
    tags=["Marketplace"]
)
security = HTTPBearer()

class MarketplaceItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    goal: str | None = Field(default=None, max_length=2000)
    description: str | None = Field(default=None, max_length=2000)
    category: str = "strategy"
    item_type: str = "strategy"
    is_public: bool = False
    data: dict = Field(default_factory=dict)

def _identity(credentials):
    return get_current_user_from_token(credentials)

def _clean(record):
    data = dict(record._mapping) if hasattr(record, "_mapping") else dict(record)
    data.pop("owner", None)
    return data


# ==========================
# SAVE STRATEGY (NO AUTH)
# ==========================
@router.post("/save", status_code=201)
async def save_strategy(data: MarketplaceItemCreate, credentials: HTTPAuthorizationCredentials = Depends(security)):
    identity = await _identity(credentials)
    organization, workspace, user = identity.get("organization"), identity.get("workspace"), identity["user"]
    if not organization or not workspace:
        raise HTTPException(409, "Complete onboarding before saving marketplace items")
    if data.category not in {"strategy", "template", "simulation", "knowledge", "automation"}:
        raise HTTPException(422, "Unsupported marketplace category")

    db = SessionLocal()

    try:

        now = datetime.now(timezone.utc).isoformat()
        query = strategies.insert().values(
            name=data.name, goal=data.goal, description=data.description,
            category=data.category, item_type=data.item_type, data=data.data,
            owner_user_id=user["id"], organization_id=organization["id"], workspace_id=workspace["id"],
            is_public=int(data.is_public), created_at=now, updated_at=now
        )

        db.execute(query)
        db.commit()

    except Exception:
        db.rollback()
        raise

    finally:

        db.close()

    return {"message": "Marketplace item saved"}


# ==========================
# GET ALL PUBLIC STRATEGIES
# ==========================
@router.get("/all")
async def get_all(credentials: HTTPAuthorizationCredentials = Depends(security)):

    db = SessionLocal()

    try:

        query = select(strategies).where(strategies.c.is_public == 1)

        result = db.execute(query)

        rows = result.fetchall()

    finally:

        db.close()

    return [
        _clean(row)
        for row in rows
    ]


# ==========================
# GET MY STRATEGIES
# ==========================
@router.get("/mine")
async def get_my(credentials: HTTPAuthorizationCredentials = Depends(security)):
    identity = await _identity(credentials)

    db = SessionLocal()

    try:

        query = (
            select(strategies)
            .where(
                strategies.c.owner_user_id == identity["user"]["id"],
                strategies.c.organization_id == identity["organization"]["id"],
            )
        )

        result = db.execute(query)

        rows = result.fetchall()

    finally:

        db.close()

    return [
        _clean(row)
        for row in rows
    ]


# ==========================
# GET SINGLE STRATEGY
# ==========================
@router.get("/{strategy_id}")
async def get_one(strategy_id: int, credentials: HTTPAuthorizationCredentials = Depends(security)):
    identity = await _identity(credentials)

    db = SessionLocal()

    try:

        query = (
            select(strategies)
            .where(strategies.c.id == strategy_id)
        )

        result = db.execute(query)

        row = result.fetchone()

    finally:

        db.close()

    if not row or (
        not row._mapping["is_public"]
        and (
            row._mapping["owner_user_id"] != identity["user"]["id"]
            or row._mapping["organization_id"] != identity["organization"]["id"]
        )
    ):
        raise HTTPException(404, "Marketplace item not found")

    return _clean(row)


# ==========================
# DELETE STRATEGY
# ==========================
@router.delete("/{strategy_id}")
async def delete(strategy_id: int, credentials: HTTPAuthorizationCredentials = Depends(security)):
    identity = await _identity(credentials)

    db = SessionLocal()

    try:

        query = (
            select(strategies)
            .where(
                strategies.c.id == strategy_id
            )
        )

        result = db.execute(query)

        strategy = result.fetchone()

        if not strategy or (
            strategy._mapping["owner_user_id"] != identity["user"]["id"]
            or strategy._mapping["organization_id"] != identity["organization"]["id"]
        ):
            raise HTTPException(404, "Marketplace item not found")

        delete_query = (
            strategies.delete()
            .where(
                strategies.c.id == strategy_id
            )
        )

        db.execute(delete_query)
        db.commit()

    except Exception:
        db.rollback()
        raise

    finally:

        db.close()

    return {"message": "Deleted"}
