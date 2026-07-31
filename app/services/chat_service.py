from app.db.database import SessionLocal

from app.core.cognitive_loop_v2 import cognitive_loop
from app.core.user_profile_engine import user_profile_engine
from app.services.memory_service import (
    memory_service,
)

from app.core.models.aura_request import AuraRequest
from app.services.aura_context_service import aura_context_service
from app.services.response_service import response_service
from app.services.session_service import session_service


class ChatService:

    async def process_chat(

        self,

        *,

        message: str,

        session_id: str,

        organization_id: int,

        workspace_id: int,

        user: dict,

    ):

        db = SessionLocal()

        try:

            # ==========================================
            # PROFILE
            # ==========================================

            profile = (
                user_profile_engine.get_profile(
                    session_id
                )
                or {}
            )

            # ==========================================
            # MEMORY
            # ==========================================

            memories = memory_service.retrieve_memories(
    db=db,
    organization_id=organization_id,
    query=message,
    limit=5,
)

            # ==========================================
            # AURA CONTEXT
            # ==========================================

            aura_context = await aura_context_service.build(
    db=db,
    organization_id=organization_id,
    workspace_id=workspace_id,
    user=user,
)

            # ==========================================
            # BUILD REQUEST
            # ==========================================

            request = AuraRequest(

                goal=message,

                profile=profile,

                organization_id=organization_id,

                workspace_id=workspace_id,

                business_context=aura_context.get(
                    "business",
                    {},
                ),

                unified_context=aura_context,

                memory=memories,

            )

            # ==========================================
            # EXECUTE
            # ==========================================

            request = await cognitive_loop.run(
                request
            )

            # ==========================================
            # STORE MEMORY
            # ==========================================

            memory_service.store_memory(
               db=db,
               organization_id=organization_id,
               content=message,
               response=str(request.response),
            )

            # ==========================================
            # BUILD RESPONSE
            # ==========================================

            response = (
                response_service.build_response(
                    request=request,
                    session_id=session_id,
                )
            )

            # ==========================================
            # SAVE SESSION
            # ==========================================

            response_payload = response if isinstance(response, dict) else {"response": str(response)}
            session_service.create_session(
                organization_id=organization_id,
                workspace_id=workspace_id,
                created_by_user_id=user["id"],
                title=message[:120],
                goal=message,
                domain="business",
                session_type="chat",
                status="completed",
                summary=response_payload.get("summary"),
                recommended_move=response_payload.get("recommended_move"),
                risk_level=response_payload.get("risk_level"),
                report_json=response_payload,
                business_model=(
                    aura_context.get("business", {})
                    .get("business_profile", {})
                    .get("business_model")
                ),
            )

            return response

        finally:

            db.close()


chat_service = ChatService()
