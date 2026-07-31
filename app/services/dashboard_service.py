from datetime import datetime, timezone

from app.services.aura_context_service import (
    aura_context_service
)

from app.services.executive_intelligence_service import (
    executive_intelligence_service
)


class DashboardService:

    """
    Executive Dashboard Builder

    Responsible for transforming Aura Context
    into a clean Executive Dashboard response.
    """

    async def build_dashboard(

        self,

        db,

        organization_id: int,

        workspace_id: int,

        user: dict

    ):

        aura_context = await aura_context_service.build(

            db=db,

            organization_id=organization_id,

            workspace_id=workspace_id,

            user=user

        )

        intelligence = executive_intelligence_service.build(
    aura_context
)

        business_snapshot = self.build_business_snapshot(

            aura_context

        )

        recommendations = self.build_recommendations(

            aura_context

        )

        recent_activity = self.build_activity(

            aura_context

        )

        actions = self.build_actions()

        return {

    "executive_brief":

        intelligence["executive_brief"],

    "business_snapshot":

        intelligence["business_snapshot"],

    "recommendations":

        intelligence["recommendations"],

    "recent_activity":

        intelligence["recent_activity"],

    "quick_actions":

        self.build_actions(),

    "generated_at":

        datetime.now(
            timezone.utc
        ).isoformat()

}

    

    # ==========================================
    # SNAPSHOT
    # ==========================================

    def build_business_snapshot(

        self,

        aura_context

    ):

        return aura_context.get(

            "business_health",

            {}

        )

    # ==========================================
    # RECOMMENDATIONS
    # ==========================================

    def build_recommendations(

        self,

        aura_context

    ):

        return aura_context.get(

            "recommendations",

            []

        )

    # ==========================================
    # ACTIVITY
    # ==========================================

    def build_activity(

        self,

        aura_context

    ):

        return aura_context.get(

            "recent_activity",

            []

        )

    # ==========================================
    # QUICK ACTIONS
    # ==========================================

    def build_actions(

        self

    ):

        return [

            {

                "title": "Ask Aura",

                "action": "chat"

            },

            {

                "title": "Run Intelligence",

                "action": "intelligence"

            },

            {

                "title": "Business Profile",

                "action": "organization"

            }

        ]


dashboard_service = DashboardService()
