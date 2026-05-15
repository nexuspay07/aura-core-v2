import re

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy import select, insert

from app.db.database import database
from app.db.organization_table import organization_table
from app.db.workspace_table import workspace_table
from app.api.auth_routes import get_current_user_from_token


router = APIRouter(
    prefix="/organizations",
    tags=["Organizations"]
)

security = HTTPBearer()


class CreateOrganizationRequest(BaseModel):
    name: str
    industry: str | None = None
    company_size: str | None = None


def make_slug(name: str):
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")

    return slug or "organization"


def clean_organization(row):
    return {
        "id": row["id"],
        "name": row["name"],
        "slug": row["slug"],
        "owner_user_id": row["owner_user_id"],
        "plan": row["plan"],
        "industry": row["industry"],
        "company_size": row["company_size"],
        "is_active": row["is_active"],
        "created_at": (
            row["created_at"].isoformat()
            if row["created_at"] else None
        ),
    }


def clean_workspace(row):
    return {
        "id": row["id"],
        "organization_id": row["organization_id"],
        "name": row["name"],
        "slug": row["slug"],
        "description": row["description"],
        "workspace_type": row["workspace_type"],
        "created_by_user_id": row["created_by_user_id"],
        "is_active": row["is_active"],
        "created_at": (
            row["created_at"].isoformat()
            if row["created_at"] else None
        ),
    }


# =========================================
# CREATE ORGANIZATION
# =========================================
@router.post("")
async def create_organization(
    data: CreateOrganizationRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    user = await get_current_user_from_token(credentials)

    # -----------------------------
    # SAFE UNIQUE SLUG GENERATION
    # -----------------------------
    base_slug = make_slug(data.name)
    final_slug = base_slug
    counter = 1

    while True:
        existing_query = select(organization_table).where(
            organization_table.c.slug == final_slug
        )

        existing = await database.fetch_one(existing_query)

        if not existing:
            break

        final_slug = f"{base_slug}-{counter}"
        counter += 1

    # -----------------------------
    # CREATE ORGANIZATION
    # -----------------------------
    query = insert(organization_table).values(
        name=data.name,
        slug=final_slug,
        owner_user_id=user["id"],
        plan="free",
        industry=data.industry,
        company_size=data.company_size,
        is_active=True,
    )

    org_id = await database.execute(query)

    # -----------------------------
    # CREATE DEFAULT WORKSPACE
    # -----------------------------
    workspace_slug = f"{final_slug}-main"

    workspace_query = insert(workspace_table).values(
        organization_id=org_id,
        name="Main Workspace",
        slug=workspace_slug,
        description="Default AURA Business workspace",
        workspace_type="business",
        created_by_user_id=user["id"],
        is_active=True,
    )

    workspace_id = await database.execute(workspace_query)

    # -----------------------------
    # FETCH CREATED RECORDS
    # -----------------------------
    org = await database.fetch_one(
        select(organization_table).where(
            organization_table.c.id == org_id
        )
    )

    workspace = await database.fetch_one(
        select(workspace_table).where(
            workspace_table.c.id == workspace_id
        )
    )

    return {
        "success": True,
        "message": "Organization created successfully",
        "organization": clean_organization(org),
        "workspace": clean_workspace(workspace),
    }


# =========================================
# LIST USER ORGANIZATIONS
# =========================================
@router.get("")
async def list_my_organizations(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    user = await get_current_user_from_token(credentials)

    query = select(organization_table).where(
        organization_table.c.owner_user_id == user["id"]
    )

    rows = await database.fetch_all(query)

    return {
        "success": True,
        "organizations": [
            clean_organization(row)
            for row in rows
        ],
    }


# =========================================
# GET SINGLE ORGANIZATION
# =========================================
@router.get("/{organization_id}")
async def get_organization(
    organization_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    user = await get_current_user_from_token(credentials)

    query = select(organization_table).where(
        organization_table.c.id == organization_id
    )

    org = await database.fetch_one(query)

    if not org:
        raise HTTPException(
            status_code=404,
            detail="Organization not found"
        )

    if org["owner_user_id"] != user["id"]:
        raise HTTPException(
            status_code=403,
            detail="Not allowed"
        )

    workspace_query = select(workspace_table).where(
        workspace_table.c.organization_id == organization_id
    )

    workspaces = await database.fetch_all(workspace_query)

    return {
        "success": True,
        "organization": clean_organization(org),
        "workspaces": [
            clean_workspace(row)
            for row in workspaces
        ],
    }