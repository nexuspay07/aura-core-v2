from sqlalchemy import select

from app.db.organization_table import (
    organization_table
)

from app.db.workspace_table import (
    workspace_table
)

from app.db.business_profile_table import (
    business_profile_table
)


class BusinessContextService:
    """
    Builds the business context that Aura
    will use before reasoning.
    """

    def build_context(
        self,
        db,
        organization_id: int,
        workspace_id: int
    ):

        # ==========================================
        # Organization
        # ==========================================

        organization = db.execute(
            select(
                organization_table
            ).where(
                organization_table.c.id == organization_id
            )
        ).fetchone()

        # ==========================================
        # Workspace
        # ==========================================

        workspace = db.execute(
            select(
                workspace_table
            ).where(
                workspace_table.c.id == workspace_id
            )
        ).fetchone()

        # ==========================================
        # Business Profile
        # ==========================================

        business_profile = db.execute(
            select(
                business_profile_table
            ).where(
                business_profile_table.c.workspace_id == workspace_id
            )
        ).fetchone()

        organization = (
            dict(organization._mapping)
            if organization
            else {}
        )

        workspace = (
            dict(workspace._mapping)
            if workspace
            else {}
        )

        business_profile = (
            dict(business_profile._mapping)
            if business_profile
            else {}
        )

        return {

            # Organization

            "organization": organization,
            "organization_name": organization.get("name"),
            "industry": organization.get("industry"),
            "company_size": organization.get("company_size"),

            # Workspace

            "workspace": workspace,
            "workspace_name": workspace.get("name"),
            "workspace_type": workspace.get("workspace_type"),

            # Business Profile

            "business_profile": business_profile,
            "mission": business_profile.get("mission"),
            "vision": business_profile.get("vision"),
            "business_stage": business_profile.get("business_stage"),
            "target_market": business_profile.get("target_market"),
            "products_services": business_profile.get("products_services"),
            "business_goals": business_profile.get("business_goals"),
            "current_challenges": business_profile.get("current_challenges"),
            "competitive_advantage": business_profile.get("competitive_advantage")
        }


business_context_service = BusinessContextService()