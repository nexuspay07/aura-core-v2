from app.db.database import SessionLocal

from app.core.cognitive_loop import (
    cognitive_loop
)

from app.core.user_profile_engine import (
    user_profile_engine
)

from app.services.memory_service import (
    save_session_memory,
    get_session_memory
)

from app.services.aura_context_service import (
    aura_context_service
)

from app.services.response_service import (
    response_service
)

from app.services.session_service import (
    session_service
)


class ChatService:
    """
    =====================================================

                    CHAT SERVICE

    Enterprise orchestration layer for Aura.

    Responsibilities

    • Build Aura Context
    • Load Memory
    • Execute Intelligence Pipeline
    • Normalize Response
    • Persist Intelligence Session

    This service MUST NOT contain
    HTTP or FastAPI logic.

    =====================================================
    """

    async def process_chat(

        self,

        *,

        message: str,

        session_id: str,

        organization_id: int,

        workspace_id: int,

        user: dict

    ) -> dict:

        # ------------------------------------
        # USER PROFILE
        # ------------------------------------

        profile = user_profile_engine.get_profile(
            session_id
        )

        # ------------------------------------
        # SESSION MEMORY
        # ------------------------------------

        previous_memories = get_session_memory(
            session_id
        )

        # ------------------------------------
        # BUILD AURA CONTEXT
        # ------------------------------------

        db = SessionLocal()

        try:

            aura_context = (
                aura_context_service.build(

                    db=db,

                    organization_id=organization_id,

                    workspace_id=workspace_id,

                    user=user

                )
            )

        finally:

            db.close()

        # ------------------------------------
        # BUILD SCENARIO
        # ------------------------------------

        scenario = {

            "goal": message,

            "aura_context": aura_context

        }

        # ------------------------------------
        # RUN INTELLIGENCE
        # ------------------------------------

        result = (
            cognitive_loop.run_intelligence_pipeline(

                goal=message,

                scenario=scenario,

                profile=profile

            )
        )

        # ------------------------------------
        # SAVE MEMORY
        # ------------------------------------

        save_session_memory(

            session_id,

            "assistant",

            str(result)

        )

        # ------------------------------------
        # BUILD API RESPONSE
        # ------------------------------------

        response = (
            response_service.build_response(

                pipeline_result=result,

                session_id=session_id,

                organization_name=(
                    aura_context["business"]
                    .get("organization_name")
                ),

                workspace_name=(
                    aura_context["business"]
                    .get("workspace_name")
                ),

                profile=profile,

                memory_count=len(
                    previous_memories
                )

            )
        )

        # ------------------------------------
        # SAVE SESSION
        # ------------------------------------

        session_service.create_session(

            organization_id=organization_id,

            workspace_id=workspace_id,

            created_by_user_id=user["id"],

            title=message[:100],

            goal=message,

            domain="business",

            session_type="decision_analysis",

            status="completed",

            summary=response["chat_response"].get(
                "message",
                ""
            ),

            recommended_move=response[
                "executive_advisor"
            ].get(
                "advisor_recommendation",
                ""
            ),

            risk_level=response[
                "chat_response"
            ].get(
                "warning",
                "unknown"
            ),

            report_json=response,

            business_model="business"

        )

        return response


chat_service = ChatService()