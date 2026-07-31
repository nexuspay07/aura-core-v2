import logging

from fastapi import HTTPException
from sqlalchemy import select
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

        # ==========================================================
        # ORGANIZATION MEMBERSHIP
        # ==========================================================

        membership = db.execute(
            select(organization_member_table)
            .where(
                organization_member_table.c.user_id == user_id
            )
            .where(
                organization_member_table.c.is_active == True
            )
        ).mappings().first()

        if not membership:
            logger.info("Onboarding required for user %s", user_id)
            return self._onboarding_identity(user)

        # ==========================================================
        # ORGANIZATION
        # ==========================================================

        organization = db.execute(
            select(organization_table)
            .where(
                organization_table.c.id ==
                membership["organization_id"]
            )
            .where(
                organization_table.c.is_active == True
            )
        ).mappings().first()

        if not organization:
            logger.warning("Active organization membership %s points to an unavailable organization", membership["id"])
            return self._onboarding_identity(user)

        # ==========================================================
        # WORKSPACE
        # ==========================================================

        workspace_query = (
            select(workspace_table)
            .where(
                workspace_table.c.organization_id ==
                organization["id"]
            )
            .where(
                workspace_table.c.is_active == True
            )
        )

        if workspace_id is not None:
            workspace_query = workspace_query.where(
                workspace_table.c.id == workspace_id
            )

        workspace = db.execute(
            workspace_query
        ).mappings().first()

        if not workspace:
            return self._onboarding_identity(user, organization=organization, organization_role=membership["role"])

        # ==========================================================
        # WORKSPACE MEMBERSHIP
        # ==========================================================

        workspace_member = db.execute(
            select(workspace_member_table)
            .where(
                workspace_member_table.c.workspace_id ==
                workspace["id"]
            )
            .where(
                workspace_member_table.c.user_id ==
                user_id
            )
            .where(
                workspace_member_table.c.is_active == True
            )
        ).mappings().first()

        if not workspace_member:

            logger.warning(
                "User %s belongs to organization %s but not workspace %s",
                user_id,
                organization["id"],
                workspace["id"],
            )

            return self._onboarding_identity(user, organization=organization, organization_role=membership["role"])

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


identity_service = IdentityService()
