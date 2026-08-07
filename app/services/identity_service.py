import logging

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.db.user_table import user_table
from app.db.organization_table import organization_table
from app.db.organization_member_table import organization_member_table
from app.db.workspace_table import workspace_table
from app.db.workspace_member_table import workspace_member_table


logger = logging.getLogger(__name__)


class IdentityService:
    """
    Enterprise Identity Service

    Resolves the authenticated user's complete identity:

        User
            ↓
        Organization Membership
            ↓
        Organization
            ↓
        Workspace Membership
            ↓
        Identity Context
    """

    def resolve(
        self,
        db: Session,
        user_id: int,
        workspace_id: int | None = None,
    ):

        # ==========================================================
        # USER
        # ==========================================================

        user = db.execute(
            select(user_table).where(
                user_table.c.id == user_id
            )
        ).mappings().first()

        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found."
            )

        # An explicit workspace is retained only for trusted internal callers;
        # normal authentication always resolves the server-controlled setting.
        selected_workspace_id = workspace_id if workspace_id is not None else user.get("active_workspace_id")
        context = self._accessible_context(db, user_id, selected_workspace_id)
        if context is None:
            context = self._fallback_context(db, user_id)
            db.execute(
                update(user_table)
                .where(user_table.c.id == user_id)
                .values(active_workspace_id=context["workspace"]["id"] if context else None)
            )
            if context is None:
                return self._onboarding_identity(dict(user))

        organization = context["organization"]
        workspace = context["workspace"]
        membership = context["organization_member"]
        workspace_member = context["workspace_member"]

        # ==========================================================
        # LOGGING
        # ==========================================================

        logger.info(
            "Identity resolved | User=%s Organization=%s Workspace=%s",
            user["id"],
            organization["id"],
            workspace["id"],
        )

        # ==========================================================
        # RETURN IDENTITY
        # ==========================================================

        return {
            "user": user,

            "organization": organization,

            "workspace": workspace,

            "organization_role": membership["role"],

            "workspace_role": workspace_member["role"],

            "onboarding_required": False,

            "permissions": {
                "organization_admin":
                    membership["role"] in ["owner", "admin"],

                "workspace_admin":
                    workspace_member["role"] == "admin",

                "can_manage_workspace":
                    workspace_member["role"] in [
                        "admin",
                        "manager",
                    ],

                "can_manage_organization":
                    membership["role"] in ["owner", "admin"],
            },
        }

    @staticmethod
    def _onboarding_identity(user, organization=None, organization_role=None):
        return {
            "user": user,
            "organization": organization,
            "workspace": None,
            "organization_role": organization_role,
            "workspace_role": None,
            "onboarding_required": True,
            "permissions": {
                "organization_admin": False,
                "workspace_admin": False,
                "can_manage_workspace": False,
                "can_manage_organization": False,
            },
        }

    @staticmethod
    def _accessible_context(db: Session, user_id: int, workspace_id: int | None):
        if workspace_id is None:
            return None
        workspace = db.execute(
            select(workspace_table).where(
                workspace_table.c.id == workspace_id,
                workspace_table.c.is_active == True,
            )
        ).mappings().first()
        if not workspace:
            return None

        organization = db.execute(
            select(organization_table).where(
                organization_table.c.id == workspace["organization_id"],
                organization_table.c.is_active == True,
            )
        ).mappings().first()
        if not organization:
            return None

        organization_member = db.execute(
            select(organization_member_table).where(
                organization_member_table.c.organization_id == organization["id"],
                organization_member_table.c.user_id == user_id,
                organization_member_table.c.is_active == True,
            )
        ).mappings().first()
        workspace_member = db.execute(
            select(workspace_member_table).where(
                workspace_member_table.c.workspace_id == workspace["id"],
                workspace_member_table.c.user_id == user_id,
                workspace_member_table.c.is_active == True,
            )
        ).mappings().first()
        if not organization_member or not workspace_member:
            return None

        return {
            "workspace": dict(workspace),
            "organization": dict(organization),
            "organization_member": dict(organization_member),
            "workspace_member": dict(workspace_member),
        }

    @classmethod
    def _fallback_context(cls, db: Session, user_id: int):
        candidates = db.execute(
            select(workspace_table.c.id)
            .join(organization_table, organization_table.c.id == workspace_table.c.organization_id)
            .join(organization_member_table, (organization_member_table.c.organization_id == organization_table.c.id) & (organization_member_table.c.user_id == user_id) & (organization_member_table.c.is_active == True))
            .join(workspace_member_table, (workspace_member_table.c.workspace_id == workspace_table.c.id) & (workspace_member_table.c.user_id == user_id) & (workspace_member_table.c.is_active == True))
            .where(workspace_table.c.is_active == True, organization_table.c.is_active == True)
            .order_by(workspace_member_table.c.created_at.asc(), workspace_member_table.c.id.asc(), workspace_table.c.id.asc())
        ).scalars().first()
        return cls._accessible_context(db, user_id, candidates)


identity_service = IdentityService()
