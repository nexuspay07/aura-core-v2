import time

import pytest

from app.intelligence_v2.contracts import DecisionType
from app.intelligence_v2.model_provider import MockModelProvider
from app.intelligence_v2.orchestrator import DecisionAnalysisOrchestrator
from app.intelligence_v2.quality import goal_tensions, normalize_goals, requested_deliverables, resource_ledger
from app.intelligence_v2.service import decision_v2_service
from app.personal.ask import analysis_report
from app.unified_intelligence.router import unified_capability_router
from tests.intelligence_v2.test_aevric_phase1 import STARTUP_CROSS_CONTEXT
from tests.intelligence_v2.test_decision_v2 import session


def startup_state(db):
    return decision_v2_service.analyze_request(db=db,user_id=1,organization_id=1,workspace_id=1,user_query=STARTUP_CROSS_CONTEXT,decision_scope="auto")


def grounded_response():
    return {"problem_summary":"Choose a sustainable path from employment to the startup.","alternatives":[{"option":"Request reduced work","benefits":["Preserves employment income while creating founder capacity"],"downsides":["Employer agreement is unknown"],"evidence_ids":["user-query"],"assumptions":[],"conditions_for_success":["Confirm the employer's terms"]},{"option":"Remain employed","benefits":["Preserves financial stability"],"downsides":["Sustained workload may worsen burnout"],"evidence_ids":["user-query"],"assumptions":[],"conditions_for_success":["Reduce workload pressure"]}],"recommended_option":"Request reduced work","rationale":"It is the most reversible way to create founder capacity while preserving income.","key_tradeoffs":["Founder time versus employment income"],"risks":["Customer concentration and unsigned expansion make an immediate irreversible move less robust"],"assumptions_used":[],"evidence_ids":["user-query"],"unresolved_questions":["Exact reduced-work compensation and workload terms"],"recommendation_change_conditions":[]}


def startup_brief(db):
    state=startup_state(db);provider=MockModelProvider(grounded_response());execution=DecisionAnalysisOrchestrator(provider).analyze(state)
    assert execution.status=="READY"
    response,_=analysis_report(state,execution)
    return state,execution,response,provider


def test_exact_startup_decision_brief_is_complete_and_single_call(session):
    state,execution,response,provider=startup_brief(session)
    assert state.classification.decision_type is DecisionType.STRATEGIC_PLANNING and not state.clarification.questions
    assert provider.calls==1 and response["recommendation"]["recommended_option"]
    assert all(response["completeness"].values())
    assert response["decision_plan"]["horizon_days"]==90 and len(response["decision_plan"]["phases"])==3
    assert execution.usage.get("repaired_claim_count",0)==0


def test_compound_goals_are_normalized_without_duplicates(session):
    goals=startup_state(session).analysis_outputs["phase2"]["goals"]
    assert len(goals)==3 and len({goal.lower() for goal in goals})==3
    assert any("primary career" in goal.lower() for goal in goals)
    assert any("financial situation" in goal.lower() for goal in goals)
    assert any("burnout" in goal.lower() for goal in goals)


def test_overlapping_goal_clauses_are_deduplicated():
    goals=normalize_goals("My goal is to grow the company.",["to grow the company","is to grow the company"])
    assert len(goals)==1


def test_conflicting_goals_create_structured_tensions():
    tensions=goal_tensions(["Preserve cash","Grow quickly"],["Stay","Expand"])
    assert tensions==[{"goal_a":"Preserve cash","goal_b":"Grow quickly","tension":"Protect stability while pursuing progress","affected_options":["Stay","Expand"]}]
    assert "weight" not in str(tensions).lower()


def test_related_goals_do_not_manufacture_a_mechanical_tension():
    assert goal_tensions(["Build durable skills","Develop useful knowledge"],["Course","Self-study"])==[]


def test_resource_ledger_separates_resources_constraints_risks_and_trends(session):
    phase=startup_state(session).analysis_outputs["phase2"]
    values=str({key:phase[key] for key in ("resources","constraints","resource_risks","trends")})
    for expected in ("$78,000","$18,000","$9,000","6.5%","$2,400","$2,100","14","45%","12%","20 hours a week","$1,500","10%"):
        assert expected in values


def test_business_financial_time_and_team_resources_are_retained(session):
    state=decision_v2_service.analyze_request(db=session,user_id=1,organization_id=1,workspace_id=1,user_query="Our 4-person team has $65k cash, $24k monthly revenue, $21k monthly expenses, and a 6-week deadline. Should we repair or defer?",decision_scope="auto")
    phase=state.analysis_outputs["phase2"]
    assert phase["resources"] and phase["constraints"] and phase["participation"]["resource"]


@pytest.mark.parametrize(("text","value","unit"),[("Give me a 30-day plan.",30,"days"),("Give me a concrete 90-day action plan.",90,"days"),("Give me a practical 6-month plan.",6,"months"),("Give me a practical 12-month plan.",12,"months")])
def test_requested_plan_horizon_is_detected(text,value,unit):
    assert requested_deliverables(text)["plan_horizon"]=={"value":value,"unit":unit}


def test_unrequested_plan_does_not_create_phases(session):
    state=decision_v2_service.analyze_request(db=session,user_id=1,organization_id=1,workspace_id=1,user_query="Our options are repair, replace, or defer. What should we do?",decision_scope="auto")
    assert "phases" not in state.analysis_outputs["phase2"]["plan"]


def test_explicit_twelve_month_plan_preserves_requested_unit(session):
    state=decision_v2_service.analyze_request(db=session,user_id=1,organization_id=1,workspace_id=1,user_query="I am deciding whether to start a diploma or study independently. Give me a practical 12-month plan.",decision_scope="personal")
    plan=state.analysis_outputs["phase2"]["plan"]
    assert plan["horizon_value"]==12 and plan["horizon_unit"]=="months" and plan["horizon_label"]=="12-Month"
    assert "horizon_days" not in plan


def test_grounded_quantitative_derivation_has_basis_and_limitation(session):
    derived=startup_state(session).derived_evidence
    coverage=next(item for item in derived if item.semantic_label=="living_expense_coverage")
    assert "7.5 months" in coverage.claim and "upper-bound" in coverage.claim and coverage.source_evidence_ids==["user-query"]


def test_unsupported_quantitative_calculation_is_not_created(session):
    state=decision_v2_service.analyze_request(db=session,user_id=1,organization_id=1,workspace_id=1,user_query="I have savings but did not provide an amount. My options are wait or proceed. What should I do?",decision_scope="auto")
    assert not any(item.semantic_label=="living_expense_coverage" for item in state.derived_evidence)


def test_missing_requested_change_condition_is_repaired_from_known_unknown(session):
    _,_,response,_=startup_brief(session)
    assert response["requested_deliverables"]["change_triggers"]
    assert response["recommendation"]["what_would_change_the_recommendation"]==["Exact reduced-work compensation and workload terms"]


def test_brief_exposes_quality_layers_not_raw_engine_dumps(session):
    _,_,response,_=startup_brief(session)
    assert response["evidence_quality"]["known"] and response["evidence_quality"]["derived"]
    assert response["decision_drivers"] and response["next_move"]
    assert not any(key in response for key in ("world_state","self_evaluation","participation"))


def test_quality_layer_overhead_and_simple_route_remain_bounded(session):
    started=time.perf_counter();startup_state(session);complex_ms=(time.perf_counter()-started)*1000
    started=time.perf_counter();route=unified_capability_router.route("Explain recurring revenue.");simple_ms=(time.perf_counter()-started)*1000
    assert complex_ms<250 and simple_ms<50 and not route.requires_decision_analysis
