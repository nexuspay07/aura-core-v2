import re
import uuid
from app.db.organization_invitation_table import (
    organization_invitation_table
)

from app.db.workspace_member_table import (
    workspace_member_table
)

from sqlalchemy import (
    select,
    insert,
    update,
    delete
)

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

from app.db.organization_member_table import (
    organization_member_table
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

class UpdateOrganizationRequest(BaseModel):

    name: str | None = None

    industry: str | None = None

    company_size: str | None = None

    plan: str | None = None

    is_active: bool | None = None

class CreateWorkspaceRequest(BaseModel):

    name: str

    description: str | None = None

    workspace_type: str = "business"

class InviteMemberRequest(BaseModel):

    email: str

    role: str = "employee"

class AcceptInvitationRequest(BaseModel):

    token: str

class AssignWorkspaceMemberRequest(BaseModel):

    user_id: int

    role: str = "member"            


def make_slug(name: str):

    slug = name.lower().strip()

    slug = re.sub(
        r"[^a-z0-9]+",
        "-",
        slug
    )

    slug = slug.strip("-")

    return slug or "organization"

def make_workspace_slug(
    organization_slug: str,
    workspace_name: str
):

    workspace_slug = make_slug(
        workspace_name
    )

    return (
        f"{organization_slug}-{workspace_slug}"
    )


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


    current_user = user["user"]
    current_user = user["user"]

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
            owner_user_id=current_user["id"],
            plan="free",
            industry=data.industry,
            company_size=data.company_size,
            is_active=True,
        )

        result = db.execute(query)

        db.commit()

        org_id = result.inserted_primary_key[0]

                # -----------------------------
        # ADD OWNER AS FIRST MEMBER
        # -----------------------------
        db.execute(

            insert(
                organization_member_table
            ).values(

                organization_id=org_id,

                user_id=current_user["id"],

                role="owner",

                status="active",

                is_active=True

            )

        )

        db.commit()

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
            created_by_user_id=current_user["id"],
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
        # ADD OWNER TO DEFAULT WORKSPACE
        # -----------------------------
        existing_workspace_member = db.execute(
            select(workspace_member_table)
            .where(
                workspace_member_table.c.workspace_id == workspace_id
            )
            .where(
                workspace_member_table.c.user_id == current_user["id"]
            )
        ).fetchone()

        if existing_workspace_member is None:

            db.execute(
                insert(
                    workspace_member_table
                ).values(
                    workspace_id=workspace_id,
                    user_id=current_user["id"],
                    role="owner",
                    status="active",
                    is_active=True
                )
            )

            db.commit()

            print("\n========== WORKSPACE MEMBERS ==========")

            members = db.execute(
                select(workspace_member_table)
            ).fetchall()

            for member in members:
                print(dict(member._mapping))

            print("=======================================\n")

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


    current_user = user["user"]
    db = SessionLocal()

    try:

        query = (
            select(organization_table)
            .where(
                organization_table.c.owner_user_id
                == current_user["id"]
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


    current_user = user["user"]
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
            != current_user["id"]
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

# =========================================
# UPDATE ORGANIZATION
# =========================================

@router.put("/{organization_id}")

async def update_organization(

    organization_id: int,

    data: UpdateOrganizationRequest,

    credentials: HTTPAuthorizationCredentials = Depends(security)

):

    user = await get_current_user_from_token(
        credentials
    )


    current_user = user["user"]
    db = SessionLocal()

    try:

        result = db.execute(

            select(
                organization_table
            ).where(

                organization_table.c.id
                == organization_id

            )

        )

        organization = result.fetchone()

        if not organization:

            raise HTTPException(

                status_code=404,

                detail="Organization not found"

            )

        organization = dict(
            organization._mapping
        )

        if organization["owner_user_id"] != current_user["id"]:

            raise HTTPException(

                status_code=403,

                detail="Not allowed"

            )

        update_data = {}

        if data.name is not None:

            update_data["name"] = data.name

        if data.industry is not None:

            update_data["industry"] = data.industry

        if data.company_size is not None:

            update_data["company_size"] = (
                data.company_size
            )

        if data.plan is not None:

            update_data["plan"] = data.plan

        if data.is_active is not None:

            update_data["is_active"] = (
                data.is_active
            )

        if update_data:

        

            db.execute(

                update(
                    organization_table
                )

                .where(

                    organization_table.c.id
                    == organization_id

                )

                .values(
                    **update_data
                )

            )

            db.commit()

        updated = db.execute(

            select(
                organization_table
            )

            .where(

                organization_table.c.id
                == organization_id

            )

        ).fetchone()

    finally:

        db.close()

    return {

        "success": True,

        "message": "Organization updated successfully.",

        "organization": clean_organization(

            dict(updated._mapping)

        )

    }

# =========================================
# CREATE WORKSPACE
# =========================================

@router.post(
    "/{organization_id}/workspaces"
)
async def create_workspace(

    organization_id: int,

    data: CreateWorkspaceRequest,

    credentials: HTTPAuthorizationCredentials = Depends(security)

):

    user = await get_current_user_from_token(
        credentials
    )


    current_user = user["user"]
    db = SessionLocal()

    try:

        result = db.execute(

            select(
                organization_table
            ).where(

                organization_table.c.id
                == organization_id

            )

        )

        organization = result.fetchone()

        if not organization:

            raise HTTPException(

                status_code=404,

                detail="Organization not found"

            )

        organization = dict(
            organization._mapping
        )

        if organization["owner_user_id"] != current_user["id"]:

            raise HTTPException(

                status_code=403,

                detail="Not allowed"

            )

        workspace_slug = make_workspace_slug(

            organization["slug"],

            data.name

        )

        counter = 1

        while True:

            existing = db.execute(

                select(
                    workspace_table
                ).where(

                    workspace_table.c.slug
                    == workspace_slug

                )

            ).fetchone()

            if not existing:

                break

            workspace_slug = (
                f"{organization['slug']}-"
                f"{make_slug(data.name)}-{counter}"
            )

            counter += 1

        result = db.execute(

            insert(
                workspace_table
            ).values(

                organization_id=organization_id,

                name=data.name,

                slug=workspace_slug,

                description=data.description,

                workspace_type=data.workspace_type,

                created_by_user_id=current_user["id"],

                is_active=True

            )

        )

        db.commit()

        workspace_id = (
            result.inserted_primary_key[0]
        )

        workspace = db.execute(

            select(
                workspace_table
            ).where(

                workspace_table.c.id
                == workspace_id

            )

        ).fetchone()

    finally:

        db.close()

    return {

        "success": True,

        "message": (
            "Workspace created successfully."
        ),

        "workspace": clean_workspace(

            dict(
                workspace._mapping
            )

        )

    }

# =========================================
# INVITE MEMBER
# =========================================

@router.post(
    "/{organization_id}/members/invite"
)
async def invite_member(

    organization_id: int,

    data: InviteMemberRequest,

    credentials: HTTPAuthorizationCredentials = Depends(security)

):

    user = await get_current_user_from_token(
        credentials
    )


    current_user = user["user"]
    db = SessionLocal()

    try:

        organization = db.execute(

            select(
                organization_table
            ).where(

                organization_table.c.id
                == organization_id

            )

        ).fetchone()

        if not organization:

            raise HTTPException(

                status_code=404,

                detail="Organization not found."

            )

        organization = dict(
            organization._mapping
        )

        if organization["owner_user_id"] != current_user["id"]:

            raise HTTPException(

                status_code=403,

                detail="Only organization owners can invite members."

            )

        invitation_token = str(
            uuid.uuid4()
        )

        db.execute(

            insert(
                organization_invitation_table
            ).values(

                organization_id=organization_id,

                email=data.email,

                role=data.role,

                status="pending",

                token=invitation_token,

                created_by_user_id=current_user["id"],

                is_active=True

            )

        )

        db.commit()

    finally:

        db.close()

    return {

        "success": True,

        "message": "Invitation created successfully.",

        "invitation_token": invitation_token
    }

# =========================================
# ACCEPT INVITATION
# =========================================

@router.post(
    "/members/accept"
)
async def accept_invitation(

    data: AcceptInvitationRequest,

    credentials: HTTPAuthorizationCredentials = Depends(security)

):

    user = await get_current_user_from_token(
        credentials
    )


    current_user = user["user"]
    db = SessionLocal()

    try:

        invitation = db.execute(

            select(
                organization_invitation_table
            ).where(

                organization_invitation_table.c.token
                == data.token

            )

        ).fetchone()

        if not invitation:

            raise HTTPException(

                status_code=404,

                detail="Invitation not found."

            )

        invitation = dict(
            invitation._mapping
        )

        if invitation["status"] != "pending":

            raise HTTPException(

                status_code=400,

                detail="Invitation already used."

            )

        db.execute(

            insert(
                organization_member_table
            ).values(

                organization_id=invitation["organization_id"],

                user_id=current_user["id"],

                role=invitation["role"],

                status="active",

                is_active=True

            )

        )

        db.execute(

            update(
                organization_invitation_table
            )

            .where(

                organization_invitation_table.c.id
                == invitation["id"]

            )

            .values(

                status="accepted"

            )

        )

        db.commit()

    finally:

        db.close()

    return {

        "success": True,

        "message": "Invitation accepted successfully."

    }

# =========================================
# ASSIGN USER TO WORKSPACE
# =========================================

@router.post(
    "/workspaces/{workspace_id}/members"
)
async def assign_workspace_member(

    workspace_id: int,

    data: AssignWorkspaceMemberRequest,

    credentials: HTTPAuthorizationCredentials = Depends(security)

):

    user = await get_current_user_from_token(
        credentials
    )


    current_user = user["user"]
    db = SessionLocal()

    try:

        workspace = db.execute(

            select(
                workspace_table
            ).where(

                workspace_table.c.id
                == workspace_id

            )

        ).fetchone()

        if not workspace:

            raise HTTPException(

                status_code=404,

                detail="Workspace not found."

            )

        workspace = dict(
            workspace._mapping
        )

        organization = db.execute(

            select(
                organization_table
            ).where(

                organization_table.c.id
                == workspace["organization_id"]

            )

        ).fetchone()

        organization = dict(
            organization._mapping
        )

        if organization["owner_user_id"] != current_user["id"]:

            raise HTTPException(

                status_code=403,

                detail="Only owners can assign workspace members."

            )

        existing = db.execute(

            select(
                workspace_member_table
            ).where(

                workspace_member_table.c.workspace_id
                == workspace_id,

                workspace_member_table.c.user_id
                == data.user_id

            )

        ).fetchone()

        if existing:

            raise HTTPException(

                status_code=400,

                detail="User already belongs to this workspace."

            )

        db.execute(

            insert(
                workspace_member_table
            ).values(

                workspace_id=workspace_id,

                user_id=data.user_id,

                role=data.role,

                status="active",

                is_active=True

            )

        )

        db.commit()

    finally:

        db.close()

    return {

        "success": True,

        "message": "Workspace member assigned successfully."

    }