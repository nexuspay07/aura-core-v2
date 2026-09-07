from app.intelligence_v2.contracts import AnalysisAlternative, AnalysisPackage, AnalysisRecommendation, AnalysisResult
from app.intelligence_v2.orchestrator import DecisionAnalysisOrchestrator, SYSTEM_PROMPT


def findings(*, analysis: str = "", rationale: str = "", condition: str = "", evidence: str = "Authorized facts."):
    package = AnalysisPackage(
        {}, {},
        [{"id": "conversation-turn:1", "content": evidence, "provenance": {}}],
        [], [], {}, [],
    )
    result = AnalysisResult(
        "problem", [], [],
        [AnalysisAlternative("option", [], [], ["conversation-turn:1"], [], [condition] if condition else [])],
        analysis,
        [],
        AnalysisRecommendation("option", rationale, "", [condition] if condition else [], []),
        [condition] if condition else [],
        [],
        ["conversation-turn:1"],
        ["conversation-turn:1"],
        [],
        [],
    )
    return DecisionAnalysisOrchestrator()._validate(result, package)


def test_evidence_identifier_number_is_not_treated_as_factual_number():
    result = findings(rationale="Use the corrected deadline [conversation-turn:1].")

    assert "unsupported numeric claim: 1" not in result


def test_real_unsupported_number_beside_citation_is_still_rejected():
    result = findings(rationale="Wait 9 months [conversation-turn:1].")

    assert "unsupported numeric claim: 9" in result
    assert "unsupported numeric claim: 1" not in result


def test_user_supplied_numeric_constraint_remains_valid_evidence():
    result = findings(rationale="Use the 30-day deadline [conversation-turn:1].", evidence="The deadline is 30 days.")

    assert "supported_literal numeric: 30" in result
    assert not any(item.startswith("unsupported numeric") for item in result)


def test_imperative_request_for_family_constraints_is_not_an_asserted_user_fact():
    result = findings(condition="List any work or family commitments that affect the plan.")

    assert "unsupported factual claim: family/personal obligation" not in result


def test_asserted_family_obligation_is_still_rejected():
    result = findings(rationale="You have family obligations, so delay the decision.")

    assert "unsupported factual claim: family/personal obligation" in result


def test_conditional_market_uncertainty_is_not_a_claim_about_current_conditions():
    result = findings(rationale="Market conditions could change while you wait.")

    assert "unsupported factual claim: future market condition" not in result


def test_asserted_market_condition_is_still_rejected():
    result = findings(rationale="The job market is favorable, so act now.")

    assert "unsupported factual claim: future market condition" in result


def test_unsupported_employment_fact_is_still_rejected():
    result = findings(rationale="Your employer allows remote work.")

    assert "unsupported factual claim: unsupported employment condition" in result


def test_provider_instruction_keeps_citations_and_unsupplied_substeps_out_of_prose():
    assert "evidence_ids fields only" in SYSTEM_PROMPT
    assert "numeric sub-deadlines" in SYSTEM_PROMPT
