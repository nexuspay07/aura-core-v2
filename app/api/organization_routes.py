import logging
import re
import uuid
from contextlib import contextmanager

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)

from pydantic import (
    BaseModel,
    Field,
)

from sqlalchemy import (
    delete,
    insert,
    select,
    update,
)
from sqlalchemy.exc import SQLAlchemyError

from app.api.auth_routes import (
    get_current_user_from_token,
)

from app.db.database import SessionLocal

from app.db.organization_table import (
    organization_table,
)

from app.db.organization_member_table import (
    organization_member_table,
)

from app.db.organization_invitation_table import (
    organization_invitation_table,
)

from app.db.workspace_table import (
    workspace_table,
)

from app.db.workspace_member_table import (
    workspace_member_table,
)

from app.db.user_table import (
    user_table,
)
from app.db.business_profile_table import business_profile_table

# ==========================================================
# ROUTER
# ==========================================================

router = APIRouter(
    prefix="/organizations",
    tags=["Organizations"],
)

security = HTTPBearer()

logger = logging.getLogger("aura.organizations")


# ==========================================================
# REQUEST MODELS
# ==========================================================


class CreateOrganizationRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    account_type: str = "business"
    industry: str | None = None
    company_size: str | None = None


class UpdateOrganizationRequest(BaseModel):
    name: str | None = None
    industry: str | None = None
    company_size: str | None = None
    plan: str | None = None
    is_active: bool | None = None


class CreateWorkspaceRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
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


# ==========================================================
# DATABASE TRANSACTION
# ==========================================================


@contextmanager
def db_session():
    db = SessionLocal()

    try:
        yield db
        db.commit()

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


# ==========================================================
# SLUG HELPERS
# ==========================================================


def make_slug(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug or "organization"


def generate_unique_slug(
    db,
    table,
    slug_column,
    base_slug: str,
) -> str:

    slug = base_slug
    counter = 1

    while db.execute(
        select(table).where(slug_column == slug)
    ).fetchone():

        slug = f"{base_slug}-{counter}"
        counter += 1

    return slug


def make_workspace_slug(
    organization_slug: str,
    workspace_name: str,
) -> str:

    return (
        f"{organization_slug}-"
        f"{make_slug(workspace_name)}"
    )


# ==========================================================
# SERIALIZERS
# ==========================================================


def clean_organization(row: dict):

    return {
        "id": row["id"],
        "name": row["name"],
        "slug": row["slug"],
        "account_type": row["account_type"],
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


def clean_workspace(row: dict):

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


# ==========================================================
# COMMON DATABASE HELPERS
# ==========================================================


def get_organization(db, organization_id: int):

    organization = db.execute(
        select(organization_table).where(
            organization_table.c.id == organization_id
        )
    ).fetchone()

    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found.",
        )

    return dict(organization._mapping)


def get_workspace(db, workspace_id: int):

    workspace = db.execute(
        select(workspace_table).where(
            workspace_table.c.id == workspace_id
        )
    ).fetchone()

    if workspace is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found.",
        )

    return dict(workspace._mapping)


def require_owner(user_id: int, organization: dict):

    if organization["owner_user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization owners can perform this action.",
        )
    
    # ==========================================================
# CREATE ORGANIZATION
# ==========================================================

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_organization(
    data: CreateOrganizationRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
):

    if data.account_type not in {"personal", "business", "enterprise"}:
        raise HTTPException(status_code=422, detail="Unsupported account type")
    identity = await get_current_user_from_token(credentials)
    current_user = identity["user"]

    with db_session() as db:

        # --------------------------------------------------
        # Prevent duplicate organization names (same owner)
        # --------------------------------------------------

        existing = db.execute(
            select(organization_table).where(
                organization_table.c.owner_user_id == current_user["id"],
                organization_table.c.name == data.name,
                organization_table.c.is_active == True,
            )
        ).fetchone()

        if existing:
            raise HTTPException(
                status_code=409,
                detail="You already have an organization with this name.",
            )

        # --------------------------------------------------
        # Create organization
        # --------------------------------------------------

        organization_slug = generate_unique_slug(
            db=db,
            table=organization_table,
            slug_column=organization_table.c.slug,
            base_slug=make_slug(data.name),
        )

        organization_result = db.execute(
            insert(organization_table).values(
                name=data.name,
                slug=organization_slug,
                owner_user_id=current_user["id"],
                plan="free",
                account_type=data.account_type,
                industry=data.industry,
                company_size=data.company_size,
                is_active=True,
            )
        )

        organization_id = organization_result.inserted_primary_key[0]

        logger.info(
            "Organization %s created by user %s",
            organization_id,
            current_user["id"],
        )

        # --------------------------------------------------
        # Organization owner
        # --------------------------------------------------

        db.execute(
            insert(organization_member_table).values(
                organization_id=organization_id,
                user_id=current_user["id"],
                role="owner",
                status="active",
                is_active=True,
            )
        )

        # --------------------------------------------------
        # Default workspace
        # --------------------------------------------------

        workspace_result = db.execute(
            insert(workspace_table).values(
                organization_id=organization_id,
                name="My Workspace" if data.account_type == "personal" else "Main Workspace",
                slug=f"{organization_slug}-main",
                description="Default workspace",
                workspace_type="personal" if data.account_type == "personal" else "business",
                created_by_user_id=current_user["id"],
                is_active=True,
            )
        )

        workspace_id = workspace_result.inserted_primary_key[0]

        logger.info(
            "Workspace %s created",
            workspace_id,
        )

        # --------------------------------------------------
        # Workspace owner
        # --------------------------------------------------

        db.execute(
            insert(workspace_member_table).values(
                workspace_id=workspace_id,
                user_id=current_user["id"],
                role="owner",
                status="active",
                is_active=True,
            )
        )

        if data.account_type != "personal":
            db.execute(
                insert(business_profile_table).values(
                    organization_id=organization_id,
                    workspace_id=workspace_id,
                    business_name=data.name,
                    business_stage="startup",
                    is_active=True,
                )
            )

        # --------------------------------------------------
        # Read created records
        # --------------------------------------------------

        organization = dict(
            db.execute(
                select(organization_table).where(
                    organization_table.c.id == organization_id
                )
            ).fetchone()._mapping
        )

        workspace = dict(
            db.execute(
                select(workspace_table).where(
                    workspace_table.c.id == workspace_id
                )
            ).fetchone()._mapping
        )

        logger.info(
            "Organization onboarding completed successfully."
        )

        return {
            "success": True,
            "message": "Organization created successfully.",
            "organization": clean_organization(organization),
            "workspace": clean_workspace(workspace),
        }
    
    # ==========================================================
# LIST MY ORGANIZATIONS
# ==========================================================

@router.get("")
async def list_my_organizations(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):

    identity = await get_current_user_from_token(credentials)
    current_user = identity["user"]

    with db_session() as db:

        rows = db.execute(

            select(
                organization_table,
                organization_member_table.c.role.label("role")
            )

            .join(

                organization_member_table,

                organization_table.c.id
                ==
                organization_member_table.c.organization_id

            )

            .where(

                organization_member_table.c.user_id
                ==
                current_user["id"]

            )

            .where(

                organization_member_table.c.is_active
                ==
                True

            )

        ).fetchall()

        organizations = []

        for row in rows:

            record = dict(row._mapping)

            organization = clean_organization(record)

            organization["role"] = record["role"]

            organizations.append(organization)

        return {

            "success": True,

            "count": len(organizations),

            "organizations": organizations

        }


# ==========================================================
# GET ORGANIZATION
# ==========================================================

@router.get("/{organization_id}")
async def get_single_organization(

    organization_id: int,

    credentials: HTTPAuthorizationCredentials = Depends(security)

):

    identity = await get_current_user_from_token(credentials)

    current_user = identity["user"]

    with db_session() as db:

        membership = db.execute(

            select(organization_member_table)

            .where(

                organization_member_table.c.organization_id
                ==
                organization_id

            )

            .where(

                organization_member_table.c.user_id
                ==
                current_user["id"]

            )

            .where(

                organization_member_table.c.is_active
                ==
                True

            )

        ).fetchone()

        if membership is None:

            raise HTTPException(

                status_code=403,

                detail="You do not belong to this organization."

            )

        organization = get_organization(

            db,

            organization_id

        )

        workspaces = db.execute(

            select(workspace_table)

            .where(

                workspace_table.c.organization_id
                ==
                organization_id

            )

            .where(

                workspace_table.c.is_active
                ==
                True

            )

        ).fetchall()

        return {

            "success": True,

            "organization": clean_organization(

                organization

            ),

            "workspaces": [

                clean_workspace(

                    dict(row._mapping)

                )

                for row in workspaces

            ]

        }


# ==========================================================
# UPDATE ORGANIZATION
# ==========================================================

@router.put("/{organization_id}")
async def update_organization(

    organization_id: int,

    data: UpdateOrganizationRequest,

    credentials: HTTPAuthorizationCredentials = Depends(security)

):

    identity = await get_current_user_from_token(credentials)

    current_user = identity["user"]

    with db_session() as db:

        organization = get_organization(

            db,

            organization_id

        )

        require_owner(

            current_user["id"],

            organization

        )

        updates = {}

        if data.name is not None:

            updates["name"] = data.name

            updates["slug"] = generate_unique_slug(

                db,

                organization_table,

                organization_table.c.slug,

                make_slug(data.name)

            )

        if data.industry is not None:

            updates["industry"] = data.industry

        if data.company_size is not None:

            updates["company_size"] = data.company_size

        if data.plan is not None:

            updates["plan"] = data.plan

        if data.is_active is not None:

            updates["is_active"] = data.is_active

        if updates:

            db.execute(

                update(

                    organization_table

                )

                .where(

                    organization_table.c.id
                    ==
                    organization_id

                )

                .values(

                    **updates

                )

            )

            logger.info(

                "Organization %s updated.",

                organization_id

            )

        updated = get_organization(

            db,

            organization_id

        )

        return {

            "success": True,

            "message": "Organization updated successfully.",

            "organization": clean_organization(

                updated

            )

        }


# ==========================================================
# DELETE ORGANIZATION (SOFT DELETE)
# ==========================================================

@router.delete("/{organization_id}")
async def delete_organization(

    organization_id: int,

    credentials: HTTPAuthorizationCredentials = Depends(security)

):

    identity = await get_current_user_from_token(credentials)

    current_user = identity["user"]

    with db_session() as db:

        organization = get_organization(

            db,

            organization_id

        )

        require_owner(

            current_user["id"],

            organization

        )

        db.execute(

            update(

                organization_table

            )

            .where(

                organization_table.c.id
                ==
                organization_id

            )

            .values(

                is_active=False

            )

        )

        db.execute(

            update(

                workspace_table

            )

            .where(

                workspace_table.c.organization_id
                ==
                organization_id

            )

            .values(

                is_active=False

            )

        )

        logger.info(

            "Organization %s archived.",

            organization_id

        )

        return {

            "success": True,

            "message": "Organization archived successfully."

        }
    
    # ==========================================================
# CREATE WORKSPACE
# ==========================================================

@router.post("/{organization_id}/workspaces")
async def create_workspace(

    organization_id: int,
    data: CreateWorkspaceRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)

):

    identity = await get_current_user_from_token(credentials)
    current_user = identity["user"]

    with db_session() as db:

        organization = get_organization(db, organization_id)

        require_owner(
            current_user["id"],
            organization
        )

        existing = db.execute(

            select(workspace_table)

            .where(
                workspace_table.c.organization_id == organization_id
            )

            .where(
                workspace_table.c.name == data.name
            )

            .where(
                workspace_table.c.is_active == True
            )

        ).fetchone()

        if existing:

            raise HTTPException(
                status_code=409,
                detail="Workspace already exists."
            )

        workspace_slug = generate_unique_slug(

            db=db,

            table=workspace_table,

            slug_column=workspace_table.c.slug,

            base_slug=make_workspace_slug(
                organization["slug"],
                data.name
            )

        )

        workspace_result = db.execute(

            insert(workspace_table).values(

                organization_id=organization_id,

                name=data.name,

                slug=workspace_slug,

                description=data.description,

                workspace_type=data.workspace_type,

                created_by_user_id=current_user["id"],

                is_active=True

            )

        )

        workspace_id = workspace_result.inserted_primary_key[0]

        db.execute(

            insert(workspace_member_table).values(

                workspace_id=workspace_id,

                user_id=current_user["id"],

                role="owner",

                status="active",

                is_active=True

            )

        )

        if organization["account_type"] != "personal":
            db.execute(
                insert(business_profile_table).values(
                    organization_id=organization_id,
                    workspace_id=workspace_id,
                    business_name=organization["name"],
                    business_stage="startup",
                    is_active=True,
                )
            )

        workspace = get_workspace(

            db,

            workspace_id

        )

        logger.info(

            "Workspace %s created for organization %s",

            workspace_id,

            organization_id

        )

        return {

            "success": True,

            "message": "Workspace created successfully.",

            "workspace": clean_workspace(

                workspace

            )

        }


# ==========================================================
# LIST WORKSPACES
# ==========================================================

@router.get("/{organization_id}/workspaces")
async def list_workspaces(

    organization_id: int,

    credentials: HTTPAuthorizationCredentials = Depends(security)

):

    identity = await get_current_user_from_token(credentials)

    current_user = identity["user"]

    with db_session() as db:

        membership = db.execute(

            select(
                organization_member_table
            )

            .where(
                organization_member_table.c.organization_id
                ==
                organization_id
            )

            .where(
                organization_member_table.c.user_id
                ==
                current_user["id"]
            )

            .where(
                organization_member_table.c.is_active
                ==
                True
            )

        ).fetchone()

        if membership is None:

            raise HTTPException(

                status_code=403,

                detail="Access denied."

            )

        rows = db.execute(

            select(
                workspace_table
            )

            .where(
                workspace_table.c.organization_id
                ==
                organization_id
            )

            .where(
                workspace_table.c.is_active
                ==
                True
            )

        ).fetchall()

        return {

            "success": True,

            "count": len(rows),

            "workspaces": [

                clean_workspace(

                    dict(row._mapping)

                )

                for row in rows

            ]

        }


# ==========================================================
# UPDATE WORKSPACE
# ==========================================================

@router.put("/workspaces/{workspace_id}")
async def update_workspace(

    workspace_id: int,

    data: CreateWorkspaceRequest,

    credentials: HTTPAuthorizationCredentials = Depends(security)

):

    identity = await get_current_user_from_token(credentials)

    current_user = identity["user"]

    with db_session() as db:

        workspace = get_workspace(

            db,

            workspace_id

        )

        organization = get_organization(

            db,

            workspace["organization_id"]

        )

        require_owner(

            current_user["id"],

            organization

        )

        updates = {

            "name": data.name,

            "description": data.description,

            "workspace_type": data.workspace_type,

        }

        if data.name:

            updates["slug"] = generate_unique_slug(

                db,

                workspace_table,

                workspace_table.c.slug,

                make_workspace_slug(

                    organization["slug"],

                    data.name

                )

            )

        db.execute(

            update(
                workspace_table
            )

            .where(
                workspace_table.c.id
                ==
                workspace_id
            )

            .values(
                **updates
            )

        )

        updated = get_workspace(

            db,

            workspace_id

        )

        logger.info(

            "Workspace %s updated.",

            workspace_id

        )

        return {

            "success": True,

            "workspace": clean_workspace(

                updated

            )

        }


# ==========================================================
# DELETE WORKSPACE
# ==========================================================

@router.delete("/workspaces/{workspace_id}")
async def archive_workspace(

    workspace_id: int,

    credentials: HTTPAuthorizationCredentials = Depends(security)

):

    identity = await get_current_user_from_token(credentials)

    current_user = identity["user"]

    with db_session() as db:

        workspace = get_workspace(

            db,

            workspace_id

        )

        organization = get_organization(

            db,

            workspace["organization_id"]

        )

        require_owner(

            current_user["id"],

            organization

        )

        db.execute(

            update(
                workspace_table
            )

            .where(
                workspace_table.c.id
                ==
                workspace_id
            )

            .values(
                is_active=False
            )

        )

        logger.info(

            "Workspace %s archived.",

            workspace_id

        )

        return {

            "success": True,

            "message": "Workspace archived successfully."

        }
    
    # ==========================================================
# INVITE MEMBER
# ==========================================================

@router.post("/{organization_id}/members/invite")
async def invite_member(

    organization_id: int,
    data: InviteMemberRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)

):

    identity = await get_current_user_from_token(credentials)
    current_user = identity["user"]

    with db_session() as db:

        organization = get_organization(
            db,
            organization_id
        )

        require_owner(
            current_user["id"],
            organization
        )

        # -----------------------------------------
        # User already belongs to organization?
        # -----------------------------------------

        existing_member = db.execute(

            select(
                organization_member_table
            )

            .where(
                organization_member_table.c.organization_id
                ==
                organization_id
            )

            .where(
                organization_member_table.c.user_id.in_(
                    select(user_table.c.id).where(
                        user_table.c.email == data.email
                    )
                )
            )

        ).fetchone()

        if existing_member:

            raise HTTPException(

                status_code=409,

                detail="User already belongs to this organization."

            )

        # -----------------------------------------
        # Pending invitation?
        # -----------------------------------------

        existing_invitation = db.execute(

            select(
                organization_invitation_table
            )

            .where(
                organization_invitation_table.c.organization_id
                ==
                organization_id
            )

            .where(
                organization_invitation_table.c.email
                ==
                data.email
            )

            .where(
                organization_invitation_table.c.status
                ==
                "pending"
            )

        ).fetchone()

        if existing_invitation:

            raise HTTPException(

                status_code=409,

                detail="Invitation already exists."

            )

        invitation_token = str(uuid.uuid4())

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

        logger.info(

            "Invitation created for %s",

            data.email

        )

        return {

            "success": True,

            "message": "Invitation created successfully.",

            "token": invitation_token

        }


# ==========================================================
# ACCEPT INVITATION
# ==========================================================

@router.post("/members/accept")
async def accept_invitation(

    data: AcceptInvitationRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)

):

    identity = await get_current_user_from_token(credentials)
    current_user = identity["user"]

    with db_session() as db:

        invitation = db.execute(

            select(
                organization_invitation_table
            )

            .where(
                organization_invitation_table.c.token
                ==
                data.token
            )

        ).fetchone()

        if invitation is None:

            raise HTTPException(

                status_code=404,

                detail="Invitation not found."

            )

        invitation = dict(invitation._mapping)

        if invitation["status"] != "pending":

            raise HTTPException(

                status_code=400,

                detail="Invitation already used."

            )

        # -----------------------------------------
        # Organization membership
        # -----------------------------------------

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

        # -----------------------------------------
        # Default workspace
        # -----------------------------------------

        workspace = db.execute(

            select(
                workspace_table
            )

            .where(
                workspace_table.c.organization_id
                ==
                invitation["organization_id"]
            )

            .where(
                workspace_table.c.is_active
                ==
                True
            )

            .order_by(
                workspace_table.c.id.asc()
            )

        ).fetchone()

        if workspace is None:

            raise HTTPException(

                status_code=500,

                detail="Organization has no active workspace."

            )

        workspace = dict(workspace._mapping)

        # -----------------------------------------
        # Add to workspace automatically
        # -----------------------------------------

        already_assigned = db.execute(

            select(
                workspace_member_table
            )

            .where(
                workspace_member_table.c.workspace_id
                ==
                workspace["id"]
            )

            .where(
                workspace_member_table.c.user_id
                ==
                current_user["id"]
            )

        ).fetchone()

        if already_assigned is None:

            db.execute(

                insert(
                    workspace_member_table
                ).values(

                    workspace_id=workspace["id"],

                    user_id=current_user["id"],

                    role="member",

                    status="active",

                    is_active=True

                )

            )

        # -----------------------------------------
        # Close invitation
        # -----------------------------------------

        db.execute(

            update(
                organization_invitation_table
            )

            .where(
                organization_invitation_table.c.id
                ==
                invitation["id"]
            )

            .values(
                status="accepted"
            )

        )

        logger.info(

            "User %s joined organization %s",

            current_user["id"],

            invitation["organization_id"]

        )

        return {

            "success": True,

            "message": "Invitation accepted successfully."

        }
    
    # ==========================================================
# LIST WORKSPACE MEMBERS
# ==========================================================

@router.get("/workspaces/{workspace_id}/members")
async def list_workspace_members(
    workspace_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):

    identity = await get_current_user_from_token(credentials)
    current_user = identity["user"]

    with db_session() as db:

        workspace = get_workspace(db, workspace_id)

        organization = get_organization(
            db,
            workspace["organization_id"]
        )

        membership = db.execute(

            select(workspace_member_table)

            .where(
                workspace_member_table.c.workspace_id == workspace_id
            )

            .where(
                workspace_member_table.c.user_id == current_user["id"]
            )

            .where(
                workspace_member_table.c.is_active == True
            )

        ).fetchone()

        if membership is None:

            require_owner(
                current_user["id"],
                organization
            )

        rows = db.execute(

            select(
                workspace_member_table,
                user_table.c.email
            )

            .join(
                user_table,
                user_table.c.id ==
                workspace_member_table.c.user_id
            )

            .where(
                workspace_member_table.c.workspace_id ==
                workspace_id
            )

            .where(
                workspace_member_table.c.is_active == True
            )

        ).fetchall()

        members = []

        for row in rows:

            record = dict(row._mapping)

            members.append({

                "user_id": record["user_id"],

                "email": record["email"],

                "role": record["role"],

                "status": record["status"]

            })

        return {

            "success": True,

            "count": len(members),

            "members": members

        }


# ==========================================================
# ASSIGN WORKSPACE MEMBER
# ==========================================================

@router.post("/workspaces/{workspace_id}/members")
async def assign_workspace_member(

    workspace_id: int,

    data: AssignWorkspaceMemberRequest,

    credentials: HTTPAuthorizationCredentials = Depends(security)

):

    identity = await get_current_user_from_token(credentials)

    current_user = identity["user"]

    with db_session() as db:

        workspace = get_workspace(
            db,
            workspace_id
        )

        organization = get_organization(
            db,
            workspace["organization_id"]
        )

        require_owner(
            current_user["id"],
            organization
        )

        organization_member = db.execute(

            select(
                organization_member_table
            )

            .where(
                organization_member_table.c.organization_id ==
                organization["id"]
            )

            .where(
                organization_member_table.c.user_id ==
                data.user_id
            )

            .where(
                organization_member_table.c.is_active ==
                True
            )

        ).fetchone()

        if organization_member is None:

            raise HTTPException(

                status_code=400,

                detail="User does not belong to the organization."

            )

        existing = db.execute(

            select(
                workspace_member_table
            )

            .where(
                workspace_member_table.c.workspace_id ==
                workspace_id
            )

            .where(
                workspace_member_table.c.user_id ==
                data.user_id
            )

        ).fetchone()

        if existing:

            raise HTTPException(

                status_code=409,

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

        logger.info(

            "User %s assigned to workspace %s",

            data.user_id,

            workspace_id

        )

        return {

            "success": True,

            "message": "Workspace member assigned successfully."

        }


# ==========================================================
# UPDATE MEMBER ROLE
# ==========================================================

@router.put("/workspaces/{workspace_id}/members/{user_id}")
async def update_workspace_member(

    workspace_id: int,

    user_id: int,

    data: AssignWorkspaceMemberRequest,

    credentials: HTTPAuthorizationCredentials = Depends(security)

):

    identity = await get_current_user_from_token(credentials)

    current_user = identity["user"]

    with db_session() as db:

        workspace = get_workspace(
            db,
            workspace_id
        )

        organization = get_organization(
            db,
            workspace["organization_id"]
        )

        require_owner(
            current_user["id"],
            organization
        )

        member = db.execute(

            select(
                workspace_member_table
            )

            .where(
                workspace_member_table.c.workspace_id ==
                workspace_id
            )

            .where(
                workspace_member_table.c.user_id ==
                user_id
            )

        ).fetchone()

        if member is None:

            raise HTTPException(

                status_code=404,

                detail="Workspace member not found."

            )

        db.execute(

            update(
                workspace_member_table
            )

            .where(
                workspace_member_table.c.workspace_id ==
                workspace_id
            )

            .where(
                workspace_member_table.c.user_id ==
                user_id
            )

            .values(
                role=data.role
            )

        )

        logger.info(

            "Workspace member role updated."

        )

        return {

            "success": True,

            "message": "Role updated successfully."

        }


# ==========================================================
# REMOVE WORKSPACE MEMBER
# ==========================================================

@router.delete("/workspaces/{workspace_id}/members/{user_id}")
async def remove_workspace_member(

    workspace_id: int,

    user_id: int,

    credentials: HTTPAuthorizationCredentials = Depends(security)

):

    identity = await get_current_user_from_token(credentials)

    current_user = identity["user"]

    with db_session() as db:

        workspace = get_workspace(
            db,
            workspace_id
        )

        organization = get_organization(
            db,
            workspace["organization_id"]
        )

        require_owner(
            current_user["id"],
            organization
        )

        member = db.execute(

            select(
                workspace_member_table
            )

            .where(
                workspace_member_table.c.workspace_id ==
                workspace_id
            )

            .where(
                workspace_member_table.c.user_id ==
                user_id
            )

        ).fetchone()

        if member is None:

            raise HTTPException(

                status_code=404,

                detail="Workspace member not found."

            )

        member = dict(member._mapping)

        if member["role"] == "owner":

            raise HTTPException(

                status_code=400,

                detail="Cannot remove the workspace owner."

            )

        db.execute(

            update(
                workspace_member_table
            )

            .where(
                workspace_member_table.c.workspace_id ==
                workspace_id
            )

            .where(
                workspace_member_table.c.user_id ==
                user_id
            )

            .values(
                is_active=False
            )

        )

        logger.info(

            "Workspace member removed."

        )

        return {

            "success": True,

            "message": "Workspace member removed successfully."

        }
