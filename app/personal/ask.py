"""Tenant-safe persistence adapter for the public Personal Ask V2 route."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import desc, insert, select, update

from app.db.intelligence_session_table import intelligence_session_table
from app.intelligence_v2.contracts import DecisionState
from app.intelligence_v2.quality import evidence_quality


class PersonalAskNotFoundError(ValueError):
    pass


def conversation_title(message: str, maximum: int = 72) -> str:
    """Create a bounded Alpha title from the user's first statement only."""
    clean = " ".join(message.strip().split()).strip(" \"'.,!?;:")
    for prefix in ("I'm thinking about ", "I am thinking about ", "I'm considering ", "I am considering "):
        if clean.lower().startswith(prefix.lower()):
            clean = clean[len(prefix):]
            break
    if not clean:
        return "Conversation"
    clean = clean[0].upper() + clean[1:]
    return clean if len(clean) <= maximum else f"{clean[:maximum - 1].rstrip()}…"


def list_owned_sessions(db, *, user_id: int, organization_id: int, workspace_id: int) -> list[dict[str, Any]]:
    rows = db.execute(
        select(intelligence_session_table).where(
            intelligence_session_table.c.created_by_user_id == user_id,
            intelligence_session_table.c.organization_id == organization_id,
            intelligence_session_table.c.workspace_id == workspace_id,
            intelligence_session_table.c.session_type == "personal_ask_v2",
            intelligence_session_table.c.is_active.is_(True),
        ).order_by(desc(intelligence_session_table.c.updated_at), desc(intelligence_session_table.c.id))
    ).mappings().all()
    conversations = []
    for row in rows:
        report = row.get("report_json") or {}
        turns = report.get("turns") if isinstance(report, dict) else []
        turns = turns if isinstance(turns, list) else []
        first_user = next((turn.get("content") for turn in turns if isinstance(turn, dict) and turn.get("role") == "user" and turn.get("content")), row.get("title") or "")
        preview = next((turn.get("content") for turn in reversed(turns) if isinstance(turn, dict) and turn.get("content")), None)
        conversations.append({
            "session_id": row["id"], "title": conversation_title(str(first_user)),
            "preview": str(preview)[:180] if preview else None, "message_count": len(turns),
            "updated_at": row.get("updated_at") or row.get("created_at"),
        })
    return conversations


def owned_session(
    db, *, session_id: int, user_id: int, organization_id: int, workspace_id: int
) -> dict[str, Any]:
    row = db.execute(
        select(intelligence_session_table).where(
            intelligence_session_table.c.id == session_id,
            intelligence_session_table.c.created_by_user_id == user_id,
            intelligence_session_table.c.organization_id == organization_id,
            intelligence_session_table.c.workspace_id == workspace_id,
            intelligence_session_table.c.is_active.is_(True),
        )
    ).mappings().first()
    if not row:
        raise PersonalAskNotFoundError("Ask session not found")
    return dict(row)


def continuation_data(session: dict[str, Any]) -> tuple[str, list[dict[str, str]]]:
    report = session.get("report_json") or {}
    personal = report.get("personal_ask") if isinstance(report, dict) else None
    if not isinstance(personal, dict) or not isinstance(personal.get("message"), str):
        raise PersonalAskNotFoundError("Ask session not found")
    answers = personal.get("clarification_answers")
    safe_answers = [
        {"question": item["question"], "answer": item["answer"]}
        for item in answers if isinstance(item, dict)
        and isinstance(item.get("question"), str)
        and isinstance(item.get("answer"), str)
    ] if isinstance(answers, list) else []
    return personal["message"], safe_answers


def create_session(db, *, user_id: int, organization_id: int, workspace_id: int, message: str) -> int:
    result = db.execute(insert(intelligence_session_table).values(
        organization_id=organization_id,
        workspace_id=workspace_id,
        created_by_user_id=user_id,
        title=conversation_title(message),
        goal=message,
        domain="personal",
        session_type="personal_ask_v2",
        status="draft",
        is_active=True,
        report_json={
            "personal_ask": {"message": message, "clarification_answers": []},
            "turns": [turn("user", message, "USER")],
        },
    ))
    return int(result.inserted_primary_key[0])


def save_session(
    db, *, session_id: int, report: dict[str, Any], status: str, summary: str | None,
    recommendation: str | None,
) -> None:
    existing = db.execute(select(intelligence_session_table.c.report_json).where(
        intelligence_session_table.c.id == session_id
    )).scalar_one_or_none() or {}
    merged = dict(existing) if isinstance(existing, dict) else {}
    for key, value in report.items():
        if key != "turns":
            merged[key] = value
    db.execute(update(intelligence_session_table).where(
        intelligence_session_table.c.id == session_id
    ).values(report_json=merged, status=status, summary=summary, recommended_move=recommendation,
             updated_at=datetime.now(timezone.utc)))


def turn(role: str, content: str, mode: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "role": role, "content": content, "mode": mode,
        "created_at": datetime.now(timezone.utc).isoformat(),
        **({"payload": payload} if payload else {}),
    }


def append_turn(db, *, session_id: int, role: str, content: str, mode: str,
                payload: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    report = db.execute(select(intelligence_session_table.c.report_json).where(
        intelligence_session_table.c.id == session_id
    )).scalar_one_or_none() or {}
    report = dict(report) if isinstance(report, dict) else {}
    turns = list(report.get("turns") or [])
    turns.append(turn(role, content, mode, payload))
    report["turns"] = turns
    db.execute(update(intelligence_session_table).where(
        intelligence_session_table.c.id == session_id
    ).values(report_json=report, updated_at=datetime.now(timezone.utc)))
    return turns


def clarification_response(state: DecisionState, *, session_id: int) -> dict[str, Any]:
    assessment = state.sufficiency
    return {
        "mode": "CLARIFICATION_REQUIRED",
        "session_id": session_id,
        "classification": state.classification.decision_type.value,
        "information_sufficiency": assessment.status.value if assessment else "insufficient",
        "questions": list(state.clarification.questions if state.clarification else []),
    }


def analysis_report(state: DecisionState, execution) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build the user-safe response and save-compatible report projection."""

    result = execution.result
    recommendation = asdict(result.recommendation)
    alternatives = [asdict(item) for item in result.alternatives]
    intelligence = state.analysis_outputs.get("phase2", {})
    deliverables = intelligence.get("requested_deliverables", {})
    assumptions = list(result.assumptions_used)
    if deliverables.get("assumptions") and not assumptions:
        assumptions = ["No additional assumptions were introduced; unresolved factors remain explicitly unknown."]
    change_conditions = list(recommendation["what_would_change_the_recommendation"])
    modelable_unknowns=[gap.suggested_question for gap in state.information_gaps if gap.can_proceed_without]
    if deliverables.get("change_triggers") and not change_conditions:
        change_conditions = list(dict.fromkeys([*result.unresolved_questions,*[gap.impact_on_decision for gap in state.information_gaps if gap.can_proceed_without]]))[:3]
    recommendation["what_would_change_the_recommendation"] = change_conditions
    quality = evidence_quality(result.key_facts, result.derived_facts, assumptions, [*result.unresolved_questions,*modelable_unknowns])
    plan = intelligence.get("plan", {})
    completeness = {
        "recommendation": bool(recommendation.get("recommended_option")),
        "tradeoffs": bool(alternatives) if deliverables.get("tradeoffs") else True,
        "assumptions": bool(assumptions) if deliverables.get("assumptions") else True,
        "uncertainty": bool(intelligence.get("uncertainties") or result.unresolved_questions) if deliverables.get("uncertainty") else True,
        "plan": bool(plan.get("phases")) if deliverables.get("plan_horizon") else True,
        "change_triggers": bool(change_conditions) if deliverables.get("change_triggers") else True,
        "normalized_goals": len({goal.lower() for goal in intelligence.get("goals", [])}) == len(intelligence.get("goals", [])),
        "grounding": not any(item.startswith("unsupported") for item in execution.critique_findings),
    }
    response = {
        "mode": "ANALYSIS_COMPLETE",
        "classification": state.classification.decision_type.value,
        "information_sufficiency": state.sufficiency.status.value if state.sufficiency else "sufficient",
        "problem_understanding": result.problem_understanding,
        "key_facts": result.key_facts,
        "derived_facts": result.derived_facts,
        "alternatives": alternatives,
        "analysis": result.analysis,
        "risks": result.risks,
        "recommendation": recommendation,
        "confidence": execution.confidence,
        "confidence_rationale": execution.confidence_rationale,
        "unresolved_questions": result.unresolved_questions,
        "limitations": result.limitations,
        "prioritized_actions": result.prioritized_actions,
        "what_would_change_recommendation": change_conditions,
        "evidence_used": result.evidence_used,
        "citations": result.citations,
        "goals": intelligence.get("goals", []),
        "competing_goals": intelligence.get("competing_goals", []),
        "goal_tensions": intelligence.get("goal_tensions", []),
        "resources": intelligence.get("resources", []),
        "constraints": intelligence.get("constraints", []),
        "resource_risks": intelligence.get("resource_risks", []),
        "trends": intelligence.get("trends", []),
        "decision_drivers": intelligence.get("decision_drivers", []),
        "uncertainties": intelligence.get("uncertainties", []),
        "causal_effects": intelligence.get("causal_effects", []),
        "decision_plan": plan,
        "requested_deliverables": deliverables,
        "evidence_quality": quality,
        "assumptions": assumptions,
        "completeness": completeness,
        "next_move": result.prioritized_actions[0] if result.prioritized_actions else (plan.get("phases", [{}])[0].get("actions", [None])[0] if plan else None),
        "engine_participation": intelligence.get("participation", {}),
        "claim_repair": execution.usage.get("claim_repair"),
        "what_changed": intelligence.get("revision_reason", []),
        "telemetry": {
            "provider_calls": 1 + int(execution.usage.get("retry_count", 0)),
            "input_tokens": execution.usage.get("input_tokens"),
            "reasoning_tokens": execution.usage.get("reasoning_tokens"),
            "visible_output_tokens": execution.usage.get("visible_output_tokens", execution.usage.get("output_tokens")),
            "total_tokens": execution.usage.get("total_tokens"),
            "provider_latency_ms": execution.usage.get("latency_ms"),
            "retry_count": execution.usage.get("retry_count", 0),
            "claim_repair_count": execution.usage.get("repaired_claim_count", 0),
            "engine_timings_ms": state.request.source_metadata.get("timings_ms", {}),
        },
    }
    from app.intelligence_v2.final_quality import finalize_decision_brief
    response = finalize_decision_brief(response, state)
    return response, {"executive_report": response}
