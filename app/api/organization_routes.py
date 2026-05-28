import re

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

from app.api.auth_routes import (
    get_current_user_from_token
)


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

    slug = re.sub(
        r"[^a-z0-9]+",
        "-",
        slug
    )

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
            if row["created_at"]
            else None
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
            if row["created_at"]
            else None
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

    user = await get_current_user_from_token(
        credentials
    )

    db = SessionLocal()

    try:

        # -----------------------------
        # SAFE UNIQUE SLUG GENERATION
        # -----------------------------
        base_slug = make_slug(data.name)

        final_slug = base_slug

        counter = 1

        while True:

            existing_query = (
                select(organization_table)
                .where(
                    organization_table.c.slug
                    == final_slug
                )
            )

            result = db.execute(
                existing_query
            )

            existing = result.fetchone()

            if not existing:
                break

            final_slug = (
                f"{base_slug}-{counter}"
            )

            counter += 1

        # -----------------------------
        # CREATE ORGANIZATION
        # -----------------------------
        query = insert(
            organization_table
        ).values(
            name=data.name,
            slug=final_slug,
            owner_user_id=user["id"],
            plan="free",
            industry=data.industry,
            company_size=data.company_size,
            is_active=True,
        )

        result = db.execute(query)

        db.commit()

        org_id = result.inserted_primary_key[0]

        # -----------------------------
        # CREATE DEFAULT WORKSPACE
        # -----------------------------
        workspace_slug = (
            f"{final_slug}-main"
        )

        workspace_query = insert(
            workspace_table
        ).values(
            organization_id=org_id,
            name="Main Workspace",
            slug=workspace_slug,
            description=(
                "Default AURA Business workspace"
            ),
            workspace_type="business",
            created_by_user_id=user["id"],
            is_active=True,
        )

        workspace_result = db.execute(
            workspace_query
        )

        db.commit()

        workspace_id = (
            workspace_result
            .inserted_primary_key[0]
        )

        # -----------------------------
        # FETCH CREATED RECORDS
        # -----------------------------
        org_result = db.execute(
            select(organization_table)
            .where(
                organization_table.c.id
                == org_id
            )
        )

        org = org_result.fetchone()

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

    finally:

        db.close()

    return {
        "success": True,
        "message": (
            "Organization created successfully"
        ),
        "organization": clean_organization(
            dict(org._mapping)
        ),
        "workspace": clean_workspace(
            dict(workspace._mapping)
        ),
    }


# =========================================
# LIST USER ORGANIZATIONS
# =========================================
@router.get("")
async def list_my_organizations(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):

    user = await get_current_user_from_token(
        credentials
    )

    db = SessionLocal()

    try:

        query = (
            select(organization_table)
            .where(
                organization_table.c.owner_user_id
                == user["id"]
            )
        )

        result = db.execute(query)

        rows = result.fetchall()

    finally:

        db.close()

    return {
        "success": True,
        "organizations": [
            clean_organization(
                dict(row._mapping)
            )
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

    user = await get_current_user_from_token(
        credentials
    )

    db = SessionLocal()

    try:

        query = (
            select(organization_table)
            .where(
                organization_table.c.id
                == organization_id
            )
        )

        result = db.execute(query)

        org = result.fetchone()

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

        workspace_query = (
            select(workspace_table)
            .where(
                workspace_table.c.organization_id
                == organization_id
            )
        )

        workspace_result = db.execute(
            workspace_query
        )

        workspaces = (
            workspace_result.fetchall()
        )

    finally:

        db.close()

    return {
        "success": True,
        "organization": clean_organization(
            org_data
        ),
        "workspaces": [
            clean_workspace(
                dict(row._mapping)
            )
            for row in workspaces
        ],
    }