from dataclasses import asdict, replace
from pathlib import Path

import pytest

from app.strategy.contracts import (
    ConfidenceLevel, EvidenceReference, StrategyAssumption, StrategyConstraint,
    StrategyInput, StrategyPhase, StrategyResult, StrategyRisk, StrategyScope,
    SuccessMeasure,
)
from app.strategy.orchestrator import StrategyOrchestrator
from app.strategy.quality import StrategyQualityError, validate_strategy_quality


def strategy_input(**changes):
    values = dict(
        scope=StrategyScope(11, 22, 33), objective="Retain key customers",
        chosen_direction="Improve service reliability",
        constraints=(StrategyConstraint("budget", "Stay within the approved $10,000 budget."),),
        evidence_refs=(EvidenceReference("evidence-1", "Reliability review"),),
        assumptions=(StrategyAssumption("The vendor remains available.", "decision"),),
        risks=(StrategyRisk("Delivery may slip."),),
        change_conditions=("Customer churn remains elevated.",),
        confidence=ConfidenceLevel.MODERATE,
        confidence_rationale=("Some execution uncertainty remains.",),
    )
    values.update(changes)
    return StrategyInput(**values)


def strategy_result(**changes):
    source = strategy_input()
    values = dict(
        scope=source.scope, objective=source.objective, chosen_direction=source.chosen_direction,
        approach="Stabilize reliability constraints before expanding the selected direction.",
        constraints=source.constraints, evidence_refs=source.evidence_refs,
        assumptions=source.assumptions + (StrategyAssumption("The team can sequence stabilization work.", "strategy_generation"),),
        phases=(
            StrategyPhase(1, "Stabilize", "Reduce reliability risk.", ("Reliability",), "Reliability improves."),
            StrategyPhase(2, "Scale", "Expand the proven approach.", ("Controlled expansion",), "Expansion remains within constraints."),
        ),
        risks=(StrategyRisk("Delivery may slip.", "Use a staged reliability review."),),
        success_measures=(
            SuccessMeasure("Reliability improves without exceeding the approved $10,000 budget."),
            SuccessMeasure("Customer retention is observably stronger."),
        ),
        change_conditions=source.change_conditions + ("Reliability does not improve after stabilization.",),
        confidence=source.confidence, confidence_rationale=source.confidence_rationale,
    )
    values.update(changes)
    return StrategyResult(**values)


def issue_codes(error):
    return {issue.code for issue in error.value.issues}


def test_minimal_and_rich_coherent_strategies_pass():
    source = strategy_input()
    validate_strategy_quality(source, strategy_result())
    minimal_source = strategy_input(assumptions=(), risks=(), change_conditions=())
    minimal_result = strategy_result(
        assumptions=(), risks=(), constraints=minimal_source.constraints,
        evidence_refs=minimal_source.evidence_refs,
        change_conditions=("Material evidence changes the direction's feasibility.",),
    )
    validate_strategy_quality(minimal_source, minimal_result)


def test_legitimate_lexical_overlap_in_approach_passes():
    validate_strategy_quality(strategy_input(), strategy_result(
        approach="Improve service reliability by stabilizing the highest-risk dependencies before controlled expansion.",
    ))


@pytest.mark.parametrize("approach", [
    "Improve service reliability",
    "IMPROVE SERVICE RELIABILITY",
    "  Improve, service reliability!!!  ",
])
def test_normalized_approach_restatement_fails(approach):
    with pytest.raises(StrategyQualityError) as error:
        validate_strategy_quality(strategy_input(), strategy_result(approach=approach))
    assert "strategy.approach_restates_direction" in issue_codes(error)


def test_distinct_phases_pass_and_normalized_duplicate_phases_fail():
    validate_strategy_quality(strategy_input(), strategy_result())
    duplicate = StrategyPhase(2, " STABILIZE! ", "reduce reliability risk", ("reliability",), "Reliability improves")
    with pytest.raises(StrategyQualityError) as error:
        validate_strategy_quality(strategy_input(), strategy_result(phases=(strategy_result().phases[0], duplicate)))
    assert "strategy.duplicate_phase" in issue_codes(error)
    assert error.value.issues[0].path == "phases[1]"


def test_distinct_success_measures_pass_and_normalized_duplicates_fail():
    validate_strategy_quality(strategy_input(), strategy_result())
    duplicate = SuccessMeasure(" reliability improves without exceeding the approved $10,000 budget!!! ")
    with pytest.raises(StrategyQualityError) as error:
        validate_strategy_quality(strategy_input(), strategy_result(success_measures=(strategy_result().success_measures[0], duplicate)))
    assert "strategy.duplicate_success_measure" in issue_codes(error)


def test_grounded_numeric_measure_passes_and_unsupported_target_fails():
    validate_strategy_quality(strategy_input(), strategy_result(
        success_measures=(SuccessMeasure("Stay within the approved $10,000 budget."),),
    ))
    with pytest.raises(StrategyQualityError) as error:
        validate_strategy_quality(strategy_input(), strategy_result(
            success_measures=(SuccessMeasure("Increase retention by 37%."),),
        ))
    assert "strategy.unsupported_numeric_target" in issue_codes(error)


def test_valid_risk_mitigation_passes_and_risk_replacement_fails():
    validate_strategy_quality(strategy_input(), strategy_result())
    with pytest.raises(StrategyQualityError) as error:
        validate_strategy_quality(strategy_input(), strategy_result(
            risks=(StrategyRisk("An invented risk.", "Invented mitigation."),),
        ))
    assert "strategy.risk_preservation_violation" in issue_codes(error)


def test_empty_mitigation_remains_a_structural_failure():
    with pytest.raises(ValueError, match="risks require"):
        validate_strategy_quality(strategy_input(), strategy_result(
            risks=(StrategyRisk("Delivery may slip.", " "),),
        ))


def test_explicit_generated_assumption_passes_and_duplicate_fails():
    validate_strategy_quality(strategy_input(), strategy_result())
    duplicate = StrategyAssumption(" the vendor remains available!!! ", "strategy_generation")
    with pytest.raises(StrategyQualityError) as error:
        validate_strategy_quality(strategy_input(), strategy_result(
            assumptions=strategy_input().assumptions + (duplicate,),
        ))
    assert "strategy.duplicate_generated_assumption" in issue_codes(error)


def test_generated_assumption_requires_explicit_strategy_source():
    with pytest.raises(StrategyQualityError) as error:
        validate_strategy_quality(strategy_input(), strategy_result(
            assumptions=strategy_input().assumptions + (StrategyAssumption("Capacity remains available.", "model"),),
        ))
    assert "strategy.invalid_generated_assumption_source" in issue_codes(error)


def test_preserved_additional_change_condition_passes_and_duplicate_fails():
    validate_strategy_quality(strategy_input(), strategy_result())
    with pytest.raises(StrategyQualityError) as error:
        validate_strategy_quality(strategy_input(), strategy_result(
            change_conditions=strategy_input().change_conditions + (" customer churn remains elevated!!! ",),
        ))
    assert "strategy.duplicate_change_condition" in issue_codes(error)


def test_assumption_and_change_condition_preservation_are_enforced():
    with pytest.raises(StrategyQualityError) as assumptions:
        validate_strategy_quality(strategy_input(), strategy_result(
            assumptions=(StrategyAssumption("Replacement.", "decision"),),
        ))
    assert "strategy.assumption_preservation_violation" in issue_codes(assumptions)
    with pytest.raises(StrategyQualityError) as conditions:
        validate_strategy_quality(strategy_input(), strategy_result(
            change_conditions=("Replacement condition.",),
        ))
    assert "strategy.change_condition_preservation_violation" in issue_codes(conditions)


def test_validator_does_not_mutate_input_or_result_and_needs_no_evidence_body():
    source, result = strategy_input(), strategy_result()
    before_source, before_result = asdict(source), asdict(result)
    validate_strategy_quality(source, result)
    assert asdict(source) == before_source and asdict(result) == before_result
    assert source.evidence_refs[0].citation_label == "Reliability review"


def test_issue_details_emit_no_tenant_or_evidence_identifiers():
    with pytest.raises(StrategyQualityError) as error:
        validate_strategy_quality(strategy_input(), strategy_result(approach="Improve service reliability"))
    rendered = str(error.value)
    for private in ("11", "22", "33", "evidence-1", "Reliability review"):
        assert private not in rendered


class Provider:
    provider_name = "quality-test"
    model_name = "offline"
    capabilities = {"structured_output"}
    def __init__(self, response): self.response=response; self.calls=0
    def generate_structured(self, **_): self.calls += 1; return self.response, {}
    def health_check(self): return True


def model_output(**changes):
    value = {
        "approach": "Stabilize reliability before controlled expansion.",
        "phases": [{"order": 1, "name": "Stabilize", "purpose": "Reduce reliability risk.", "focus_areas": ["Reliability"], "milestone_intent": None}],
        "risk_mitigations": [],
        "success_measures": ["Reliability improves."],
        "assumptions": [], "uncertainties": [],
        "change_conditions": ["Reliability does not improve."],
    }
    value.update(changes)
    return value


def test_orchestrator_runs_structural_then_quality_validation(monkeypatch):
    import app.strategy.orchestrator as module
    order = []
    structural, quality = module.validate_strategy_result, module.validate_strategy_quality
    monkeypatch.setattr(module, "validate_strategy_result", lambda *args: (order.append("structural"), structural(*args))[1])
    monkeypatch.setattr(module, "validate_strategy_quality", lambda *args: (order.append("quality"), quality(*args))[1])
    StrategyOrchestrator(Provider(model_output())).generate(strategy_input())
    assert order == ["structural", "quality"]


def test_quality_failure_prevents_return_without_additional_provider_call():
    provider = Provider(model_output(approach="Improve, service reliability!!!"))
    with pytest.raises(StrategyQualityError):
        StrategyOrchestrator(provider).generate(strategy_input())
    assert provider.calls == 1
    assert StrategyOrchestrator.max_provider_calls == 2


def test_quality_validation_is_provider_free_and_platform_independent():
    source = Path("app/strategy/quality.py").read_text(encoding="utf-8").lower()
    for forbidden in (
        "modelprovider", "generate_structured", "fastapi", "sessionlocal", "requests", "httpx",
        "personal_ask", "control_center", "simulation", "app.learning", "app.execution",
        "app.core.agents", "marketplace", "random", "datetime.now", "open(",
    ):
        assert forbidden not in source
