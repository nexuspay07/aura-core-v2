"""Public, capability-gated Personal Ask endpoint backed by Intelligence V2."""

from __future__ import annotations

import json
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.api.auth_routes import get_current_user_from_token
from app.db.database import SessionLocal
from app.intelligence_v2.orchestrator import decision_analysis_orchestrator
from app.intelligence_v2.service import decision_v2_service
from app.intelligence_v2.documents import document_evidence_retriever
from app.personal.ask import (
    PersonalAskNotFoundError,
    analysis_report,
    append_turn,
    clarification_response,
    continuation_data,
    list_owned_sessions,
    create_session,
    owned_session,
    save_session,
)
from app.unified_intelligence.orchestrator import unified_aura_orchestrator
from app.intelligence_v2.model_provider import ProviderTimeoutError, ProviderUnavailableError


router = APIRouter(prefix="/personal", tags=["Personal Ask"])
security = HTTPBearer()
logger = logging.getLogger(__name__)


class PersonalAskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str | None = Field(default=None, min_length=1, max_length=12000)
    session_id: int | None = Field(default=None, gt=0)
    clarification_response: str | None = Field(default=None, min_length=1, max_length=4000)

    @model_validator(mode="after")
    def validate_turn(self):
        if self.session_id is None and not self.message:
            raise ValueError("message is required for a new ask")
        if self.session_id is not None and self.message and self.clarification_response:
            raise ValueError("submit either a new message or a clarification response")
        if self.session_id is not None and not (self.message or self.clarification_response):
            raise ValueError("message or clarification_response is required")
        return self


async def current_identity(credentials: HTTPAuthorizationCredentials = Depends(security)):
    return await get_current_user_from_token(credentials)


def scope(identity: dict) -> tuple[int, int, int]:
    user = identity.get("user") or {}
    organization = identity.get("organization") or {}
    workspace = identity.get("workspace") or {}
    if "ask_aura" not in identity.get("capabilities", []):
        raise HTTPException(status_code=404, detail="Personal Ask is not available")
    if not all(isinstance(item.get("id"), int) for item in (user, organization, workspace)):
        raise HTTPException(status_code=404, detail="Personal workspace not found")
    return user["id"], organization["id"], workspace["id"]


def _log_provider_failure(status_name: str, diagnostics: dict | None) -> None:
    """Development diagnostics: retain only an explicit non-sensitive allowlist."""
    diagnostics = diagnostics or {}
    fields = ("provider", "model", "error_category", "exception_type", "error_code", "error_type", "http_status", "provider_status", "response_status", "response_state", "latency_ms", "failure_stage", "validation_categories", "validation_finding_count", "structured_parse_status", "rejected_numeric_values")
    record = {field: diagnostics.get(field) for field in fields if diagnostics.get(field) is not None}
    record.update({"product_route": "/personal/ask", "analysis_status": status_name})
    logger.warning("personal_ask_provider_failure %s", json.dumps(record, sort_keys=True))


def _failure(status_name: str, diagnostics: dict | None = None):
    _log_provider_failure(status_name, diagnostics)
    if status_name == "ANALYSIS_PROVIDER_UNAVAILABLE":
        raise HTTPException(status_code=503, detail="Aura is temporarily unavailable. Please try again later.")
    if status_name == "RETRYABLE_FAILURE":
        raise HTTPException(status_code=504, detail="Aura timed out. Please try again later.")
    if status_name == "ANALYSIS_FAILED":
        raise HTTPException(status_code=422, detail="Aura could not safely validate this analysis.")
    raise HTTPException(status_code=500, detail="Aura analysis failed")


def _safe_usage(usage: dict | None) -> dict:
    allowed = ("provider", "model", "latency_ms", "input_tokens", "output_tokens", "reasoning_tokens", "total_tokens")
    return {key: usage[key] for key in allowed if usage and usage.get(key) is not None}


@router.post("/ask")
async def ask(body: PersonalAskRequest, identity=Depends(current_identity)):
    user_id, organization_id, workspace_id = scope(identity)
    db = SessionLocal()
    try:
        is_new_session = body.session_id is None
        if is_new_session:
            message = body.message.strip()
            session_id = create_session(
                db, user_id=user_id, organization_id=organization_id,
                workspace_id=workspace_id, message=message,
            )
            answers: list[dict[str, str]] = []
        else:
            session = owned_session(
                db, session_id=body.session_id, user_id=user_id,
                organization_id=organization_id, workspace_id=workspace_id,
            )
            message, answers = continuation_data(session)
            session_id = body.session_id
            if body.message:
                message = body.message.strip()
                answers = []
                save_session(db, session_id=session_id, report={"personal_ask": {"message": message, "clarification_answers": []}}, status="draft", summary=None, recommendation=None)
                append_turn(db, session_id=session_id, role="user", content=message, mode="USER")

        route = unified_aura_orchestrator.prepare(message)
        if not route.requires_decision_analysis:
            stored = owned_session(db, session_id=session_id, user_id=user_id,
                                   organization_id=organization_id, workspace_id=workspace_id)
            prior_turns = (stored.get("report_json") or {}).get("turns") or []
            documents = document_evidence_retriever.retrieve(
                db=db, organization_id=organization_id, workspace_id=workspace_id, query=message,
            ) if route.requires_document_evidence else []
            result = unified_aura_orchestrator.answer_non_decision(
                message, route, turns=prior_turns[:-1], document_evidence=documents,
            )
            reply = result["message"]
            report = {
                "personal_ask": {"message": message, "clarification_answers": []},
                "conversation": {"response": reply},
                "model_usage": _safe_usage(result.get("usage")),
            }
            save_session(db, session_id=session_id, report=report, status="completed", summary=reply, recommendation=None)
            public_payload = {"sources": result.get("sources", [])} if result["mode"] in {"CURRENT_COMPLETE", "CURRENT_INFORMATION_UNAVAILABLE"} else None
            turns = append_turn(db, session_id=session_id, role="assistant", content=reply, mode=result["mode"], payload=public_payload)
            db.commit()
            return {"mode": result["mode"], "session_id": session_id, "message": reply, "turns": turns, **({"sources": result.get("sources", [])} if public_payload else {})}

        stored = owned_session(db, session_id=session_id, user_id=user_id,
                               organization_id=organization_id, workspace_id=workspace_id)
        session_turns = (stored.get("report_json") or {}).get("turns") or []
        state = decision_v2_service.analyze_request(
            db=db, user_id=user_id, organization_id=organization_id,
            workspace_id=workspace_id, user_query=message, session_id=session_id,
            decision_scope="personal",
            conversation_turns=session_turns[:-1],
        )
        for answer in answers:
            state = decision_v2_service.apply_clarification_answer(state=state, **answer)
        if body.clarification_response:
            question = next(iter(state.clarification_state.unresolved_questions), None)
            if question is None:
                raise HTTPException(status_code=409, detail="This Ask session does not need clarification")
            state = decision_v2_service.apply_clarification_answer(
                state=state, question=question, answer=body.clarification_response.strip(),
            )
            answers = [*answers, {"question": question, "answer": body.clarification_response.strip()}]
            append_turn(db, session_id=session_id, role="user", content=body.clarification_response.strip(), mode="USER")

        if state.analysis_status == "CLARIFICATION_REQUIRED":
            report = {"personal_ask": {"message": message, "clarification_answers": answers}}
            save_session(db, session_id=session_id, report=report, status="clarification_required", summary=None, recommendation=None)
            questions = list(state.clarification.questions if state.clarification else [])
            turns = append_turn(db, session_id=session_id, role="assistant", content=questions[0] if questions else "I need a little more information.", mode="CLARIFICATION_REQUIRED", payload={"questions": questions})
            db.commit()
            response = clarification_response(state, session_id=session_id)
            response["turns"] = turns
            return response

        execution = decision_analysis_orchestrator.analyze(state)
        if execution.status != "READY":
            db.rollback()
            _failure(execution.status, execution.usage)
        response, report = analysis_report(state, execution)
        report["personal_ask"] = {"message": message, "clarification_answers": answers}
        save_session(
            db, session_id=session_id, report=report, status="completed",
            summary=response["problem_understanding"],
            recommendation=response["recommendation"]["recommended_option"],
        )
        turns = append_turn(db, session_id=session_id, role="assistant", content=response["recommendation"]["recommended_option"], mode="ANALYSIS_COMPLETE", payload=dict(response))
        db.commit()
        response["session_id"] = session_id
        response["turns"] = turns
        return response
    except ProviderTimeoutError:
        db.rollback()
        _failure("RETRYABLE_FAILURE", {"failure_stage": "general_generation"})
    except ProviderUnavailableError as error:
        db.rollback()
        _failure("ANALYSIS_PROVIDER_UNAVAILABLE", error.diagnostics)
    except PersonalAskNotFoundError:
        db.rollback()
        raise HTTPException(status_code=404, detail="Ask session not found")
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@router.get("/ask/{session_id}")
async def get_ask_session(session_id: int, identity=Depends(current_identity)):
    user_id, organization_id, workspace_id = scope(identity)
    db = SessionLocal()
    try:
        session = owned_session(db, session_id=session_id, user_id=user_id,
                                organization_id=organization_id, workspace_id=workspace_id)
        if session.get("session_type") != "personal_ask_v2":
            raise PersonalAskNotFoundError("Ask session not found")
        report = session.get("report_json") or {}
        executive = report.get("executive_report")
        turns = report.get("turns") or []
        return {
            "session_id": session_id, "status": session.get("status"), "turns": turns,
            "mode": "ANALYSIS_COMPLETE" if executive else "CLARIFICATION_REQUIRED" if session.get("status") == "clarification_required" else "CONVERSATION",
            "classification": executive.get("classification") if isinstance(executive, dict) else None,
            "decision": executive,
            "pending_clarification": session.get("status") == "clarification_required",
            "questions": ((turns[-1].get("payload") or {}).get("questions", []) if turns else []),
        }
    except PersonalAskNotFoundError:
        raise HTTPException(status_code=404, detail="Ask session not found")
    finally:
        db.close()


@router.get("/conversations")
async def get_conversations(identity=Depends(current_identity)):
    user_id, organization_id, workspace_id = scope(identity)
    db = SessionLocal()
    try:
        return list_owned_sessions(db, user_id=user_id, organization_id=organization_id, workspace_id=workspace_id)
    finally:
        db.close()
