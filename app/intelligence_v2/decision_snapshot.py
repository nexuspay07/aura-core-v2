"""Explicit, privacy-allowlisted canonical Decision execution snapshot."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from app.intelligence_v2.contracts import AnalysisExecution, DecisionState


SNAPSHOT_SCHEMA_VERSION = 1


class DecisionSnapshotValidationError(ValueError):
    pass


def _text(value: Any, field: str, *, optional: bool = False) -> str | None:
    if value is None and optional:
        return None
    if not isinstance(value, str) or not value.strip():
        raise DecisionSnapshotValidationError(f"{field} must be meaningful")
    return value.strip()


def _texts(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise DecisionSnapshotValidationError(f"{field} must be an ordered collection")
    return tuple(_text(item, f"{field}[{index}]") for index, item in enumerate(value))


@dataclass(frozen=True)
class CanonicalDecisionSnapshotV1:
    decision_type: str
    objective: str
    selected_option: str
    constraints: tuple[str, ...]
    resources: tuple[dict[str, str], ...]
    evidence_references: tuple[dict[str, str | None], ...]
    assumptions: tuple[dict[str, str], ...]
    alternatives: tuple[dict[str, Any], ...]
    risks: tuple[str, ...]
    uncertainties: tuple[str, ...]
    time_horizon: str | None
    change_conditions: tuple[str, ...]
    confidence: str
    confidence_rationale: tuple[str, ...]
    schema_version: int = SNAPSHOT_SCHEMA_VERSION

    @classmethod
    def capture(cls, state: DecisionState, execution: AnalysisExecution) -> "CanonicalDecisionSnapshotV1":
        if not isinstance(state, DecisionState) or not isinstance(execution, AnalysisExecution):
            raise DecisionSnapshotValidationError("authoritative DecisionState and AnalysisExecution are required")
        if execution.status != "READY" or execution.result is None:
            raise DecisionSnapshotValidationError("a READY Decision execution is required")
        phase2 = state.analysis_outputs.get("phase2", {})
        if not isinstance(phase2, Mapping):
            raise DecisionSnapshotValidationError("phase2 output must be structured")
        evidence = {item.id: item for item in state.evidence}
        analysis = execution.result
        payload = {
            "schema_version": SNAPSHOT_SCHEMA_VERSION,
            "decision_type": getattr(state.request.decision_type, "value", state.request.decision_type),
            # The request's explicit parsed objective is preferred. For legacy
            # READY states where the deterministic fact ledger found no goal,
            # the authoritative request question is the objective verbatim.
            "objective": state.request.objective or state.request.user_query,
            "selected_option": analysis.recommendation.recommended_option,
            "constraints": state.request.constraints,
            "resources": [{"type": item.get("type"), "value": item.get("value")} for item in phase2.get("resources", []) if isinstance(item, Mapping)],
            "evidence_references": [{"evidence_id": item, "citation_label": evidence[item].citation_label if item in evidence else None} for item in analysis.evidence_used],
            "assumptions": ([{"statement": item.statement, "source": item.source} for item in state.assumptions] + [{"statement": item, "source": "decision_analysis"} for item in analysis.assumptions_used]),
            "alternatives": [{"option": item.option, "benefits": item.benefits, "downsides": item.downsides, "evidence_ids": item.evidence_ids, "assumptions": item.assumptions, "conditions_for_success": item.conditions_for_success} for item in analysis.alternatives],
            "risks": analysis.risks,
            "uncertainties": phase2.get("uncertainties", []),
            "time_horizon": state.request.timeframe,
            "change_conditions": analysis.recommendation.what_would_change_the_recommendation,
            "confidence": execution.confidence,
            "confidence_rationale": execution.confidence_rationale,
        }
        return cls.from_dict(payload)

    @classmethod
    def from_dict(cls, value: Any) -> "CanonicalDecisionSnapshotV1":
        if not isinstance(value, Mapping):
            raise DecisionSnapshotValidationError("snapshot must be an object")
        expected = set(cls.__dataclass_fields__)
        if set(value) != expected:
            raise DecisionSnapshotValidationError("snapshot fields do not match schema version 1")
        if value.get("schema_version") != SNAPSHOT_SCHEMA_VERSION:
            raise DecisionSnapshotValidationError("unsupported snapshot schema version")
        resources = value.get("resources")
        evidence = value.get("evidence_references")
        assumptions = value.get("assumptions")
        alternatives = value.get("alternatives")
        if not all(isinstance(item, (list, tuple)) for item in (resources, evidence, assumptions, alternatives)):
            raise DecisionSnapshotValidationError("snapshot collections must be ordered")
        normalized_resources = tuple({"type": _text(item.get("type"), "resource type"), "value": _text(item.get("value"), "resource value")} for item in resources if isinstance(item, Mapping))
        if len(normalized_resources) != len(resources): raise DecisionSnapshotValidationError("resource must be structured")
        normalized_evidence = tuple({"evidence_id": _text(item.get("evidence_id"), "evidence ID"), "citation_label": _text(item.get("citation_label"), "citation label", optional=True)} for item in evidence if isinstance(item, Mapping))
        if len(normalized_evidence) != len(evidence): raise DecisionSnapshotValidationError("evidence reference must be structured")
        normalized_assumptions = tuple({"statement": _text(item.get("statement"), "assumption"), "source": _text(item.get("source"), "assumption source")} for item in assumptions if isinstance(item, Mapping))
        if len(normalized_assumptions) != len(assumptions): raise DecisionSnapshotValidationError("assumption must be structured")
        normalized_alternatives = []
        for item in alternatives:
            if not isinstance(item, Mapping): raise DecisionSnapshotValidationError("alternative must be structured")
            normalized_alternatives.append({"option": _text(item.get("option"), "alternative option"), "benefits": list(_texts(item.get("benefits"), "alternative benefits")), "downsides": list(_texts(item.get("downsides"), "alternative downsides")), "evidence_ids": list(_texts(item.get("evidence_ids"), "alternative evidence")), "assumptions": list(_texts(item.get("assumptions"), "alternative assumptions")), "conditions_for_success": list(_texts(item.get("conditions_for_success"), "alternative conditions"))})
        confidence = _text(value.get("confidence"), "confidence")
        if confidence not in {"HIGH", "MODERATE", "LOW"}: raise DecisionSnapshotValidationError("confidence must be HIGH, MODERATE, or LOW")
        return cls(decision_type=_text(value.get("decision_type"), "decision type"), objective=_text(value.get("objective"), "objective"), selected_option=_text(value.get("selected_option"), "selected option"), constraints=_texts(value.get("constraints"), "constraints"), resources=normalized_resources, evidence_references=normalized_evidence, assumptions=normalized_assumptions, alternatives=tuple(normalized_alternatives), risks=_texts(value.get("risks"), "risks"), uncertainties=_texts(value.get("uncertainties"), "uncertainties"), time_horizon=_text(value.get("time_horizon"), "time horizon", optional=True), change_conditions=_texts(value.get("change_conditions"), "change conditions"), confidence=confidence, confidence_rationale=_texts(value.get("confidence_rationale"), "confidence rationale"))

    def to_dict(self) -> dict[str, Any]:
        return {"decision_type": self.decision_type, "objective": self.objective, "selected_option": self.selected_option, "constraints": list(self.constraints), "resources": [dict(x) for x in self.resources], "evidence_references": [dict(x) for x in self.evidence_references], "assumptions": [dict(x) for x in self.assumptions], "alternatives": [dict(x) for x in self.alternatives], "risks": list(self.risks), "uncertainties": list(self.uncertainties), "time_horizon": self.time_horizon, "change_conditions": list(self.change_conditions), "confidence": self.confidence, "confidence_rationale": list(self.confidence_rationale), "schema_version": self.schema_version}
