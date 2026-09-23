from dataclasses import FrozenInstanceError, asdict, fields
import json
from pathlib import Path

import pytest

from app.strategy.contracts import (
    ConfidenceLevel,
    EvidenceReference,
    StrategyAssumption,
    StrategyConstraint,
    StrategyPhase,
    StrategyResource,
    StrategyResult,
    StrategyRisk,
    StrategyScope,
    SuccessMeasure,
)
from app.strategy.presentation import StrategyPresentation, to_strategy_presentation


def canonical_result():
    return StrategyResult(
        scope=StrategyScope(11, 22, 33),
        objective="Retain key customers exactly as stated.",
        chosen_direction="Improve reliability before expansion.",
        approach="Stabilize critical dependencies, then expand deliberately.",
        phases=(
            StrategyPhase(1, "Stabilize", "Reduce reliability risk.", ("Operations",), "Reliability improves."),
            StrategyPhase(2, "Expand", "Extend the proven approach.", ("Growth",), None),
        ),
        constraints=(StrategyConstraint("budget", "Stay within the approved budget."),),
        resources=(StrategyResource("Delivery team", "Existing delivery capacity."),),
        risks=(
            StrategyRisk("Delivery may slip.", "Use staged reviews."),
            StrategyRisk("Adoption may be uneven."),
        ),
        success_measures=(
            SuccessMeasure("Reliability improves.", "evidence-1"),
            SuccessMeasure("Retention becomes observably stronger."),
        ),
        assumptions=(
            StrategyAssumption("The vendor remains available.", "decision"),
            StrategyAssumption("The team can sequence the work.", "strategy_generation"),
        ),
        uncertainties=("Future demand remains uncertain.", "Supplier timing may change."),
        change_conditions=("Reliability does not improve.", "Constraints materially change."),
        confidence=ConfidenceLevel.MODERATE,
        confidence_rationale=("Execution uncertainty remains.",),
        time_horizon="Next planning horizon",
        evidence_refs=(EvidenceReference("evidence-1", "Reliability review"),),
        source_decision_id=71,
        source_reference="personal-decision:71",
        strategy_id="internal-strategy-id",
        version=9,
    )


def test_maps_canonical_content_exactly_and_preserves_ordering():
    source = canonical_result()
    result = to_strategy_presentation(source)

    assert result.objective == source.objective
    assert result.chosen_direction == source.chosen_direction
    assert result.approach == source.approach
    assert tuple(item.name for item in result.phases) == ("Stabilize", "Expand")
    assert tuple(item.risk for item in result.risks) == ("Delivery may slip.", "Adoption may be uneven.")
    assert tuple(item.mitigation for item in result.risks) == ("Use staged reviews.", None)
    assert tuple(item.condition for item in result.success_measures) == (
        "Reliability improves.",
        "Retention becomes observably stronger.",
    )
    assert tuple(item.statement for item in result.assumptions) == (
        "The vendor remains available.",
        "The team can sequence the work.",
    )
    assert tuple(item.source for item in result.assumptions) == ("decision", "strategy_generation")
    assert result.uncertainties == source.uncertainties
    assert result.change_conditions == source.change_conditions


def test_preserves_confidence_time_horizon_source_and_safe_evidence_references():
    result = to_strategy_presentation(canonical_result())

    assert result.confidence is ConfidenceLevel.MODERATE
    assert not isinstance(result.confidence, (int, float))
    assert result.confidence_rationale == ("Execution uncertainty remains.",)
    assert result.time_horizon == "Next planning horizon"
    assert result.source_decision_id == 71
    assert result.source_reference == "personal-decision:71"
    assert asdict(result.evidence_references[0]) == {
        "evidence_id": "evidence-1",
        "citation_label": "Reliability review",
    }


def test_excludes_tenant_internal_and_noncanonical_presentation_fields():
    names = {item.name for item in fields(StrategyPresentation)}
    assert names.isdisjoint({
        "scope", "user_id", "organization_id", "workspace_id", "strategy_id", "version",
        "provider", "model", "prompt", "raw_output", "telemetry", "risk_score",
        "risk_probability", "confidence_score", "progress", "alternatives",
    })
    rendered = json.dumps(asdict(to_strategy_presentation(canonical_result())))
    for excluded in ("internal-strategy-id", '"user_id"', '"organization_id"', '"workspace_id"'):
        assert excluded not in rendered


def test_mapping_is_immutable_nonmutating_deterministic_and_json_compatible():
    source = canonical_result()
    before = asdict(source)
    first = to_strategy_presentation(source)
    second = to_strategy_presentation(source)

    assert first == second
    assert asdict(source) == before
    with pytest.raises(FrozenInstanceError):
        first.approach = "Rewritten"
    assert json.loads(json.dumps(asdict(first)))["confidence"] == "MODERATE"


def test_mapper_does_not_invent_metrics_targets_or_identifiers():
    source = canonical_result()
    rendered = json.dumps(asdict(to_strategy_presentation(source)))

    assert "95%" not in rendered
    assert "risk_score" not in rendered
    assert "progress" not in rendered
    assert "strategy_id" not in rendered
    assert tuple(item.condition for item in to_strategy_presentation(source).success_measures) == tuple(
        item.condition for item in source.success_measures
    )


def test_presentation_module_has_no_side_effect_or_product_dependencies():
    source = Path("app/strategy/presentation.py").read_text(encoding="utf-8").lower()
    for forbidden in (
        "fastapi", "sqlalchemy", "sessionlocal", "repository", "personal_ask",
        "marketplace", "commercial", "billing", "control_center", "telemetry",
        "simulation", "planning", "app.learning", "app.execution", "app.core.agents",
        "modelprovider", "generate_structured", "open(", "requests", "httpx",
    ):
        assert forbidden not in source
