"""Deterministic reproduction of Phase 6.1 live grounding failures."""

from dataclasses import asdict

from app.intelligence_v2.contracts import DecisionType
from app.intelligence_v2.model_provider import MockModelProvider
from app.intelligence_v2.orchestrator import DecisionAnalysisOrchestrator
from app.intelligence_v2.service import decision_v2_service
from tests.intelligence_v2.test_decision_v2 import session

CAR = "I have $32,000 in savings and I'm thinking about buying a car for $18,000 in cash. I earn $4,200 per month and my regular expenses are about $2,600. I want to keep at least $20,000 in emergency savings. Should I buy the car now, choose something cheaper, or wait?"
EDUCATION = "I've been accepted into a 2-year college program that costs $8,000 per year, but I also have a full-time job paying $45,000. I want better long-term career opportunities, but I'm worried about losing income while studying. Should I go back to school now?"


def state(db, query):
    return decision_v2_service.analyze_request(db=db,user_id=1,organization_id=1,workspace_id=1,user_query=query,decision_scope="personal")


def response(*, summary, option, rationale, evidence_ids):
    return {"problem_summary":summary,"alternatives":[{"option":option,"benefits":[rationale],"downsides":[],"evidence_ids":evidence_ids,"assumptions":[],"conditions_for_success":[]}],"recommended_option":option,"rationale":rationale,"key_tradeoffs":[],"risks":[],"assumptions_used":[],"evidence_ids":evidence_ids,"unresolved_questions":[],"recommendation_change_conditions":[]}


def test_car_arithmetic_is_authorized_derived_evidence(session):
    decision=state(session,CAR)
    derived={item.id:item for item in decision.derived_evidence}
    assert decision.classification.decision_type is DecisionType.MAJOR_PURCHASE
    assert {"derived:monthly_surplus","derived:savings_after_purchase","derived:emergency_savings_gap"} <= set(derived)
    assert derived["derived:monthly_surplus"].source_evidence_ids == ["user-query"]
    assert derived["derived:savings_after_purchase"].source_values["remaining"] == "14000"
    assert derived["derived:emergency_savings_gap"].source_values["gap"] == "6000"
    raw=response(summary="Buying a car",option="Wait or choose a cheaper car",rationale="The cash purchase leaves $14,000, which is $6,000 below the stated reserve target; monthly surplus is $1,600.",evidence_ids=["user-query","derived:monthly_surplus","derived:savings_after_purchase","derived:emergency_savings_gap"])
    execution=DecisionAnalysisOrchestrator(MockModelProvider(raw)).analyze(decision)
    assert execution.status == "READY", (execution.critique_findings,asdict(execution.result) if execution.result else None)


def test_education_total_tuition_is_authorized_but_foregone_income_is_not(session):
    decision=state(session,EDUCATION)
    assert decision.classification.decision_type is DecisionType.EDUCATION_DECISION
    assert len(decision.derived_evidence)==1 and decision.derived_evidence[0].source_values["total_tuition"]=="16000"
    supported=response(summary="Going back to school",option="Compare study formats",rationale="Stated tuition totals $16,000; lost income remains uncertain.",evidence_ids=["user-query","derived:total_stated_tuition"])
    assert DecisionAnalysisOrchestrator(MockModelProvider(supported)).analyze(decision).status=="READY"
    unsupported=response(summary="Going back to school",option="Enroll",rationale="You will lose $90,000 of income.",evidence_ids=["user-query"])
    rejected=DecisionAnalysisOrchestrator(MockModelProvider(unsupported)).analyze(decision)
    assert rejected.status=="ANALYSIS_FAILED"
    assert rejected.usage["failure_stage"]=="grounding_validation"
    assert rejected.usage["validation_categories"]==["unsupported_numeric_claim"]


def test_sanitized_failure_categories_distinguish_citation_and_grounding(session):
    decision=state(session,CAR)
    raw=response(summary="Buying a car",option="Buy",rationale="An unsupported fact.",evidence_ids=["invented-source"])
    execution=DecisionAnalysisOrchestrator(MockModelProvider(raw)).analyze(decision)
    assert execution.status=="ANALYSIS_FAILED"
    assert execution.usage["failure_stage"]=="grounding_validation"
    assert "citation_rejection" in execution.usage["validation_categories"]
    assert "invented-source" not in str(execution.usage)
