"""Tenant-safe Personal Decision persistence and lifecycle service."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError

from app.db.intelligence_session_table import intelligence_session_table
from app.db.personal_decision_table import personal_decision_table


DECISION_STATUSES = frozenset({"open", "decided", "awaiting_outcome", "completed"})
OUTCOME_STATUSES = frozenset({"not_recorded", "pending", "recorded"})
DECISION_TYPES = frozenset({
    "career_decision", "education_decision", "major_purchase", "personal_finance",
    "personal_project", "relocation", "life_planning", "decision_analysis", "general",
})
_FORWARD_TRANSITIONS = {
    "open": {"decided"},
    "decided": {"awaiting_outcome"},
    "awaiting_outcome": {"completed"},
    "completed": set(),
}
_SNAPSHOT_FIELDS = (
    "problem_understanding", "key_facts", "derived_facts", "alternatives",
    "recommendation", "confidence", "confidence_rationale", "unresolved_factors",
    "assumptions", "limitations", "what_would_change_recommendation",
)


class PersonalDecisionError(ValueError):
    pass


class PersonalDecisionNotFoundError(PersonalDecisionError):
    pass


class PersonalDecisionTransitionError(PersonalDecisionError):
    pass


class PersonalDecisionAlreadySavedError(PersonalDecisionError):
    pass


def _text(value: Any) -> str | None:
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return None


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()][:12]


def _alternatives(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    curated = []
    for item in value[:5]:
        if not isinstance(item, dict):
            continue
        option = _text(item.get("option") or item.get("name"))
        if option:
            curated.append({
                "option": option,
                "benefits": _string_list(item.get("benefits")),
                "downsides": _string_list(item.get("downsides")),
            })
    return curated


def display_title(question: str, decision_type: str, summary: str | None = None) -> str:
    """Create a concise display title without changing the retained question."""
    text = (question or "").lower()
    if decision_type == "major_purchase" and "car" in text:
        return "Buying a car"
    if decision_type == "education_decision" and "school" in text:
        return "Going back to school"
    if decision_type == "career_decision" and "job offer" in text:
        return "Choosing between job offers"
    labels = {"personal_finance": "A personal finance decision", "relocation": "A relocation decision", "personal_project": "A personal project", "career_decision": "A career decision", "education_decision": "An education decision", "life_planning": "A personal decision"}
    candidate = _text(summary) or labels.get(decision_type) or "A personal decision"
    return candidate if len(candidate) <= 100 else f"{candidate[:99].rstrip()}…"


def curate_session_snapshot(session: dict[str, Any]) -> dict[str, Any]:
    """Copy only durable, user-meaningful fields from an owned source session."""

    report = session.get("report_json") or {}
    if not isinstance(report, dict):
        report = {}
    report = report.get("executive_report", report)
    if not isinstance(report, dict):
        report = {}
    recommendation_value = report.get("recommendation") or report.get("recommended_move") or session.get("recommended_move")
    if isinstance(recommendation_value, dict):
        recommendation_value = recommendation_value.get("recommendation") or recommendation_value.get("rationale")
    confidence = report.get("confidence")
    confidence_value = _text(confidence.get("level")) if isinstance(confidence, dict) else _text(confidence)
    confidence_rationale = _text(report.get("confidence_rationale"))
    snapshot = {
        "problem_understanding": _text(report.get("problem_understanding") or report.get("executive_summary") or session.get("summary")) or "No summary was retained.",
        "key_facts": _string_list(report.get("key_facts")),
        "derived_facts": _string_list(report.get("derived_facts")),
        "alternatives": _alternatives(report.get("alternatives")),
        "recommendation": _text(recommendation_value) or "No recommendation was retained.",
        "confidence": confidence_value,
        "confidence_rationale": confidence_rationale,
        "unresolved_factors": _string_list(report.get("unresolved_questions") or report.get("unresolved_factors")),
        "assumptions": _string_list(report.get("assumptions")),
        "limitations": _string_list(report.get("limitations")),
        "what_would_change_recommendation": _string_list(report.get("what_would_change_recommendation") or report.get("recommendation_change_conditions")),
    }
    return snapshot


class PersonalDecisionRepository:
    def get_owned(self, db, *, decision_id: int, user_id: int, organization_id: int, workspace_id: int) -> dict[str, Any]:
        row = db.execute(
            select(personal_decision_table).where(
                personal_decision_table.c.id == decision_id,
                personal_decision_table.c.user_id == user_id,
                personal_decision_table.c.organization_id == organization_id,
                personal_decision_table.c.workspace_id == workspace_id,
            )
        ).mappings().first()
        if not row:
            raise PersonalDecisionNotFoundError("Decision not found")
        return dict(row)

    def list_owned(self, db, *, user_id: int, organization_id: int, workspace_id: int, status: str | None, decision_type: str | None) -> list[dict[str, Any]]:
        query = select(personal_decision_table).where(
            personal_decision_table.c.user_id == user_id,
            personal_decision_table.c.organization_id == organization_id,
            personal_decision_table.c.workspace_id == workspace_id,
        )
        if status:
            query = query.where(personal_decision_table.c.status == status)
        if decision_type:
            query = query.where(personal_decision_table.c.decision_type == decision_type)
        return [dict(row) for row in db.execute(query.order_by(personal_decision_table.c.updated_at.desc(), personal_decision_table.c.id.desc())).mappings().all()]


class PersonalDecisionService:
    def __init__(self, repository: PersonalDecisionRepository | None = None):
        self.repository = repository or PersonalDecisionRepository()

    @staticmethod
    def _owned_source_session(db, *, source_session_id: int, user_id: int, organization_id: int, workspace_id: int) -> dict[str, Any]:
        row = db.execute(
            select(intelligence_session_table).where(
                intelligence_session_table.c.id == source_session_id,
                intelligence_session_table.c.created_by_user_id == user_id,
                intelligence_session_table.c.organization_id == organization_id,
                intelligence_session_table.c.workspace_id == workspace_id,
                intelligence_session_table.c.is_active.is_(True),
            )
        ).mappings().first()
        if not row:
            raise PersonalDecisionNotFoundError("Decision source not found")
        return dict(row)

    def create(self, db, *, user_id: int, organization_id: int, workspace_id: int, source_session_id: int, title: str | None, decision_type: str) -> dict[str, Any]:
        if decision_type not in DECISION_TYPES:
            raise PersonalDecisionError("Unsupported decision type")
        source = self._owned_source_session(db, source_session_id=source_session_id, user_id=user_id, organization_id=organization_id, workspace_id=workspace_id)
        if db.execute(select(personal_decision_table.c.id).where(personal_decision_table.c.source_session_id == source_session_id)).first():
            raise PersonalDecisionAlreadySavedError("A decision has already been saved from this Ask session")
        snapshot = curate_session_snapshot(source)
        try:
            result = db.execute(personal_decision_table.insert().values(
                user_id=user_id,
                organization_id=organization_id,
                workspace_id=workspace_id,
                source_session_id=source_session_id,
                title=_text(title) or display_title(source["goal"], decision_type, snapshot.get("problem_understanding")),
                original_question=source["goal"],
                decision_type=decision_type,
                status="open",
                analysis_snapshot_json=snapshot,
                recommendation=snapshot["recommendation"],
                confidence=snapshot["confidence"],
                confidence_rationale=snapshot["confidence_rationale"],
                outcome_status="not_recorded",
            ))
        except IntegrityError as error:
            raise PersonalDecisionAlreadySavedError("A decision has already been saved from this Ask session") from error
        return self.repository.get_owned(db, decision_id=result.inserted_primary_key[0], user_id=user_id, organization_id=organization_id, workspace_id=workspace_id)

    def update(self, db, *, decision_id: int, user_id: int, organization_id: int, workspace_id: int, changes: dict[str, Any]) -> dict[str, Any]:
        decision = self.repository.get_owned(db, decision_id=decision_id, user_id=user_id, organization_id=organization_id, workspace_id=workspace_id)
        values: dict[str, Any] = {"updated_at": datetime.now(timezone.utc)}
        requested_status = changes.get("status")
        requested_outcome = changes.get("outcome_status")
        current_status = decision["status"]

        if requested_status is not None:
            if requested_status not in DECISION_STATUSES:
                raise PersonalDecisionError("Unsupported decision status")
            if requested_status != current_status and requested_status not in _FORWARD_TRANSITIONS[current_status]:
                raise PersonalDecisionTransitionError(f"Cannot transition decision from {current_status} to {requested_status}")
            values["status"] = requested_status

        if "user_choice" in changes:
            choice = _text(changes["user_choice"])
            if not choice:
                raise PersonalDecisionError("User choice must not be blank")
            if current_status not in {"open", "decided"}:
                raise PersonalDecisionTransitionError("User choice can only be recorded before outcome tracking")
            values["user_choice"] = choice
            if "user_choice_rationale" in changes:
                values["user_choice_rationale"] = _text(changes["user_choice_rationale"])
            values["decision_date"] = changes.get("decision_date") or decision.get("decision_date") or datetime.now(timezone.utc)
            if requested_status is None and current_status == "open":
                values["status"] = "decided"

        if "review_date" in changes:
            values["review_date"] = changes["review_date"]

        effective_status = values.get("status", current_status)
        effective_outcome = requested_outcome if requested_outcome is not None else decision["outcome_status"]
        if effective_status == "awaiting_outcome" and requested_outcome is None:
            effective_outcome = "pending"
        if requested_outcome is not None and requested_outcome not in OUTCOME_STATUSES:
            raise PersonalDecisionError("Unsupported outcome status")
        if effective_status == "completed" and effective_outcome != "recorded":
            raise PersonalDecisionTransitionError("Completed decisions require a recorded outcome status")
        if effective_outcome == "recorded" and effective_status not in {"awaiting_outcome", "completed"}:
            raise PersonalDecisionTransitionError("Outcomes can only be recorded after a decision awaits an outcome")
        values["outcome_status"] = effective_outcome

        db.execute(update(personal_decision_table).where(personal_decision_table.c.id == decision_id).values(**values))
        return self.repository.get_owned(db, decision_id=decision_id, user_id=user_id, organization_id=organization_id, workspace_id=workspace_id)

    def delete(self, db, *, decision_id: int, user_id: int, organization_id: int, workspace_id: int) -> None:
        self.repository.get_owned(db, decision_id=decision_id, user_id=user_id, organization_id=organization_id, workspace_id=workspace_id)
        db.execute(delete(personal_decision_table).where(personal_decision_table.c.id == decision_id))


personal_decision_service = PersonalDecisionService()
