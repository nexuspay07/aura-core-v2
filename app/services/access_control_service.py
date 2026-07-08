from sqlalchemy import (
    select
)

from app.db.organization_member_table import (
    organization_member_table
)

from app.db.workspace_member_table import (
    workspace_member_table
)


class AccessControlService:
    """
    ====================================================

            ENTERPRISE ACCESS CONTROL SERVICE

    Responsibilities

    • Validate organization membership

    • Validate workspace membership

    • Resolve effective roles

    • Build permission model

    • Supply access context

    This service NEVER performs business logic.

    ====================================================
    """

    def resolve_access(

        self,

        db,

        user_id: int,

        organization_id: int,

        workspace_id: int

    ):

        # ---------------------------------------
        # ORGANIZATION MEMBERSHIP
        # ---------------------------------------

        organization = db.execute(

            select(
                organization_member_table
            ).where(

                organization_member_table.c.organization_id
                == organization_id

            ).where(

                organization_member_table.c.user_id
                == user_id

            ).where(

                organization_member_table.c.is_active
                == True

            )

        ).fetchone()

        if not organization:

            raise PermissionError(

                "User does not belong to this organization."

            )

        organization = dict(
            organization._mapping
        )

        # ---------------------------------------
        # WORKSPACE MEMBERSHIP
        # ---------------------------------------

        workspace = db.execute(

            select(
                workspace_member_table
            ).where(

                workspace_member_table.c.workspace_id
                == workspace_id

            ).where(

                workspace_member_table.c.user_id
                == user_id

            )

        ).fetchone()

        if not workspace:

            raise PermissionError(

                "User does not belong to this workspace."

            )

        workspace = dict(
            workspace._mapping
        )

        # ---------------------------------------
        # BUILD PERMISSIONS
        # ---------------------------------------

        permissions = self._build_permissions(

            organization["role"],

            workspace["role"]

        )

        return {

            "organization_role":
                organization["role"],

            "workspace_role":
                workspace["role"],

            "permissions":
                permissions

        }

    def _build_permissions(

        self,

        organization_role,

        workspace_role

    ):

        permissions = {

            "chat": False,

            "dashboard": False,

            "marketplace": False,

            "sessions": False,

            "analytics": False,

            "memory": False,

            "manage_workspace": False,

            "manage_members": False,

            "manage_organization": False

        }

        # ---------------------------------------
        # ORGANIZATION ROLES
        # ---------------------------------------

        if organization_role == "owner":

            for permission in permissions:
                permissions[permission] = True

            return permissions

        if organization_role == "admin":

            permissions["chat"] = True
            permissions["dashboard"] = True
            permissions["marketplace"] = True
            permissions["sessions"] = True
            permissions["analytics"] = True
            permissions["memory"] = True
            permissions["manage_workspace"] = True
            permissions["manage_members"] = True

        elif organization_role == "manager":

            permissions["chat"] = True
            permissions["dashboard"] = True
            permissions["sessions"] = True
            permissions["analytics"] = True

        elif organization_role == "member":

            permissions["chat"] = True
            permissions["dashboard"] = True
            permissions["sessions"] = True

        elif organization_role == "guest":

            permissions["dashboard"] = True

        # ---------------------------------------
        # WORKSPACE ROLE OVERRIDES
        # ---------------------------------------

        if workspace_role == "workspace_admin":

            permissions["manage_workspace"] = True

        if workspace_role == "editor":

            permissions["chat"] = True

        if workspace_role == "analyst":

            permissions["analytics"] = True

        return permissions


access_control_service = AccessControlService()