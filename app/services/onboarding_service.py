import re

from sqlalchemy import insert, select, update

from app.db.user_table import user_table

from app.db.organization_table import (
    organization_table
)

from app.db.workspace_table import (
    workspace_table
)

from app.db.organization_member_table import (
    organization_member_table
)

from app.db.workspace_member_table import (
    workspace_member_table
)
from app.db.business_profile_table import business_profile_table


class OnboardingService:

    """
    Enterprise Onboarding Service

    Responsible for provisioning a new
    organization and workspace for every
    newly registered user.
    """

    def initialize(

        self,

        db,

        user_id: int,

        full_name: str | None,
        account_type: str = "business",
        organization_name: str | None = None,
        industry: str | None = None,
        company_size: str | None = None,
        workspace_name: str | None = None,

    ):

        # ------------------------------------
        # ORGANIZATION NAME
        # ------------------------------------

        if account_type not in {"personal", "business", "enterprise"}:
            raise ValueError("Unsupported account type")

        is_personal = account_type == "personal"
        organization_name = (
            "Personal Space"
            if is_personal
            else organization_name or (
                f"{full_name}'s Organization" if full_name else "My Organization"
            )
        )
        workspace_name = "My Workspace" if is_personal else workspace_name or "Main Workspace"

        base_slug = re.sub(r"[^a-z0-9]+", "-", organization_name.lower()).strip("-") or "organization"
        organization_slug = base_slug
        suffix = 1
        while db.execute(select(organization_table.c.id).where(organization_table.c.slug == organization_slug)).first():
            organization_slug = f"{base_slug}-{suffix}"
            suffix += 1

        # ------------------------------------
        # CREATE ORGANIZATION
        # ------------------------------------

        organization_result = db.execute(

            insert(
                organization_table
            ).values(

                name=organization_name,

                slug=organization_slug,

                owner_user_id=user_id,

                plan="free",

                subscription_status="inactive",
                account_type=account_type,
                industry=None if is_personal else industry,
                company_size=None if is_personal else company_size,

                is_active=True

            )

        )

        organization_id = (

            organization_result

            .inserted_primary_key[0]

        )

        # ------------------------------------
        # CREATE DEFAULT WORKSPACE
        # ------------------------------------

        workspace_result = db.execute(

            insert(
                workspace_table
            ).values(

                organization_id=organization_id,

                name=workspace_name,

                slug=f"{organization_slug}-main",

                description="Default workspace",

                workspace_type="personal" if is_personal else "business",

                created_by_user_id=user_id,

                is_active=True

            )

        )

        workspace_id = (

            workspace_result

            .inserted_primary_key[0]

        )

        # ------------------------------------
        # ORGANIZATION MEMBERSHIP
        # ------------------------------------

        db.execute(

            insert(
                organization_member_table
            ).values(

                organization_id=organization_id,

                user_id=user_id,

                role="owner",

                status="active",

                is_active=True

            )

        )

        # ------------------------------------
        # WORKSPACE MEMBERSHIP
        # ------------------------------------

        db.execute(

            insert(
                workspace_member_table
            ).values(

                workspace_id=workspace_id,

                user_id=user_id,

                role="owner",

                status="active",

                is_active=True

            )

        )

        if not is_personal:
            db.execute(
                insert(business_profile_table).values(
                    organization_id=organization_id,
                    workspace_id=workspace_id,
                    business_name=organization_name,
                    industry=industry,
                    business_stage="startup",
                    is_active=True,
                )
            )

        db.execute(
            update(user_table)
            .where(user_table.c.id == user_id)
            .values(active_workspace_id=workspace_id)
        )

        return {

            "organization_id": organization_id,

            "workspace_id": workspace_id

        }


onboarding_service = OnboardingService()
