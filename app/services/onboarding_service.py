import re

from sqlalchemy import insert, select

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

        full_name: str | None

    ):

        # ------------------------------------
        # ORGANIZATION NAME
        # ------------------------------------

        organization_name = (

            f"{full_name}'s Organization"

            if full_name

            else "My Organization"

        )

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

                name="Main Workspace",

                slug=f"{organization_slug}-main",

                description="Default workspace",

                workspace_type="business",

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

        db.execute(
            insert(business_profile_table).values(
                organization_id=organization_id,
                workspace_id=workspace_id,
                business_name=organization_name,
                business_stage="startup",
                is_active=True,
            )
        )

        return {

            "organization_id": organization_id,

            "workspace_id": workspace_id

        }


onboarding_service = OnboardingService()
