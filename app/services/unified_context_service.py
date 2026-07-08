from app.services.business_context_service import (
    business_context_service
)


class UnifiedContextService:
    """
    =====================================================

                UNIFIED CONTEXT SERVICE

    The Unified Context Service aggregates every
    domain-specific context into a single unified
    object before Aura builds its platform context.

    This service should NEVER contain business logic.

    It simply combines context from multiple
    providers.

    Current Providers

    • Business Context

    Future Providers

    • Memory Context

    • Marketplace Context

    • Knowledge Context

    • Activity Context

    • Permissions Context

    • Simulation Context

    =====================================================
    """

    def build(

        self,

        db,

        organization_id: int,

        workspace_id: int

    ):

        business_context = (

            business_context_service.build_context(

                db,

                organization_id,

                workspace_id

            )

        )

        return {

            "business": business_context,

            "providers": {

                "business": True,

                "memory": False,

                "knowledge": False,

                "marketplace": False,

                "permissions": False,

                "activity": False,

                "simulation": False

            }

        }


unified_context_service = UnifiedContextService()