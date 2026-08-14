from fastapi import HTTPException
from sqlalchemy import select

from app.core.cognitive_loop_v2 import cognitive_loop
from app.core.models.aura_request import AuraRequest
from app.db.database import SessionLocal
from app.db.intelligence_session_table import intelligence_session_table
from app.services.aura_context_service import aura_context_service
from app.services.memory_service import memory_service
from app.services.response_service import response_service
from app.services.session_service import session_service


class ChatService:
    """Execute one Decision Center request within a single persistence transaction."""

    @staticmethod
    def _owned_session(db, session_id: int, organization_id: int, workspace_id: int, user_id: int):
        session = db.execute(
            select(intelligence_session_table.c.id).where(
                intelligence_session_table.c.id == session_id,
                intelligence_session_table.c.organization_id == organization_id,
                intelligence_session_table.c.workspace_id == workspace_id,
                intelligence_session_table.c.created_by_user_id == user_id,
                intelligence_session_table.c.is_active.is_(True),
            )
        ).first()
        if not session:
            # Keep tenant boundaries opaque: foreign and missing sessions look alike.
            raise HTTPException(status_code=404, detail="Intelligence session not found")
        return session.id

    async def process_chat(
        self,
        *,
        message: str,
        session_id: int | None,
        organization_id: int,
        workspace_id: int,
        user: dict,
    ) -> dict:
        db = SessionLocal()
        try:
            user_id = user["id"]
            if session_id is not None:
                self._owned_session(db, session_id, organization_id, workspace_id, user_id)

            # File-backed profiles are a legacy global store. They are intentionally
            # excluded from the authenticated production path until they are durable
            # and tenant-scoped.
            profile = {}
            memories = memory_service.retrieve_memories(
                db=db, organization_id=organization_id, query=message, limit=5
            )
            aura_context = await aura_context_service.build(
                db=db,
                organization_id=organization_id,
                workspace_id=workspace_id,
                user=user,
            )
            request = AuraRequest(
                goal=message,
                profile=profile,
                organization_id=organization_id,
                workspace_id=workspace_id,
                business_context=aura_context.get("business", {}),
                unified_context=aura_context,
                memory=memories,
            )
            request = await cognitive_loop.run(request)
            response = response_service.build_response(request=request, session_id=session_id)

            # This deliberately joins the same transaction as the session write.
            # A report/session failure therefore rolls the memory write back too.
            memory_service.store_memory(
                db=db,
                organization_id=organization_id,
                workspace_id=workspace_id,
                user_id=user_id,
                content=message,
                response=str(request.response),
                commit=False,
            )

            if session_id is None:
                session_id = session_service.create_session(
                    organization_id=organization_id,
                    workspace_id=workspace_id,
                    created_by_user_id=user_id,
                    title=message[:120],
                    goal=message,
                    domain="business",
                    session_type="chat",
                    status="completed",
                    summary=response.get("summary"),
                    recommended_move=response.get("recommended_move"),
                    risk_level=response.get("risk_level"),
                    report_json=response,
                    business_model=(
                        aura_context.get("business", {})
                        .get("business_profile", {})
                        .get("business_model")
                    ),
                    db=db,
                    commit=False,
                )

            response["session_id"] = session_id
            session_service.update_report(
                session_id=session_id, report_json=response, db=db, commit=False
            )
            db.commit()
            return response
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()


chat_service = ChatService()
