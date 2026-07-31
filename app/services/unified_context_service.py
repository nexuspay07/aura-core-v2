from app.services.business_context_service import business_context_service
from app.services.identity_service import identity_service
from app.services.external_context_service import external_context_service
from app.services.memory_service import memory_service
from app.services.knowledge_service import knowledge_service


class UnifiedContextService:
    """
    =====================================================

                UNIFIED CONTEXT SERVICE

    Aggregates all platform context into a single object.

    This service performs NO business logic.

    It simply collects context from other services.

    =====================================================
    """

    async def build(
        self,
        db,
        organization_id: int,
        workspace_id: int,
        user_id: int | None = None,
    ):

        business_context = (
            business_context_service.build_context(
                db,
                organization_id,
                workspace_id,
            )
        )

        identity_context = (
            identity_service.build_context(
                db=db,
                user_id=user_id,
            )
            if user_id
            else {}
        )

        # External context is generated later during executive processing.
        external_context = {}

        # Placeholder until integrations are complete
        memory_context = {}
        knowledge_context = {}

        return {

            "business": business_context,

            "identity": identity_context,

            "external": external_context,

            "memory": memory_context,

            "knowledge": knowledge_context,

            "providers": {

                "business": True,
                "identity": True,
                "external": True,
                "memory": bool(memory_context),
                "knowledge": bool(knowledge_context),

            },

        }


unified_context_service = UnifiedContextService()