import time

from app.intelligence_v2.model_provider import MockModelProvider
from app.intelligence_v2.orchestrator import DecisionAnalysisOrchestrator
from app.intelligence_v2.service import decision_v2_service
from app.unified_intelligence.orchestrator import unified_aura_orchestrator
from tests.intelligence_v2.test_aevric_phase1 import SCENARIO_A,SCENARIO_B
from tests.intelligence_v2.test_analysis_orchestrator import response
from tests.intelligence_v2.test_decision_v2 import session

def analyze(db,text,turns=None):
    return decision_v2_service.analyze_request(db=db,user_id=1,organization_id=1,workspace_id=1,user_query=text,decision_scope="auto",conversation_turns=turns)

def test_scenario_a_models_goals_resources_uncertainty_and_plan(session):
    phase=analyze(session,SCENARIO_A).analysis_outputs["phase2"]
    assert len(phase["goals"])>=2 and len(phase["resources"])>=5 and phase["uncertainties"]
    assert phase["participation"]["multi_goal"] and phase["participation"]["resource"] and phase["participation"]["planning"]

def test_scenario_b_repairs_one_unsupported_claim_and_finishes(session):
    state=analyze(session,SCENARIO_B);raw=response();raw["rationale"]="Allocate 3 engineers while protecting the supplied operating constraints."
    execution=DecisionAnalysisOrchestrator(MockModelProvider(raw)).analyze(state)
    assert not state.clarification.questions and state.classification.decision_type.value=="strategic_planning"
    assert execution.status=="READY" and execution.usage["repaired_numeric_values"]==["3"]
    assert not any("unsupported numeric" in item for item in execution.critique_findings)

def test_scenario_c_new_revenue_supersedes_stale_revenue(session):
    state=analyze(session,"Monthly revenue rose to $40k.",[{"role":"user","content":"Monthly revenue was $24k."}])
    values=[item["value"] for item in state.request.source_metadata["fact_ledger"]["facts"] if item["type"]=="revenue"]
    assert values==["$40k"] and "$24k" not in state.request.user_query
    assert state.analysis_outputs["phase2"]["revision_reason"]

def test_scenario_d_competing_goals_have_tensions_without_weights(session):
    state=analyze(session,"Our goals are growth, security, health, time, and optionality. Should we stay, reduce scope, or pause?")
    phase=state.analysis_outputs["phase2"]
    assert len(phase["competing_goals"])==5 and 0<len(phase["goal_tensions"])<4
    assert "weight" not in str(phase).lower() and "Balance '" not in str(phase)

def test_scenario_e_infeasible_resource_plan_is_flagged(session):
    state=analyze(session,"Our 4-person team has a $4k budget and 6-week deadline. Hiring 2 engineers costs $9k monthly. Should we hire or reduce scope?")
    phase=state.analysis_outputs["phase2"]
    assert phase["participation"]["resource"] and phase["plan"]["feasible"] is False
    assert phase["self_evaluation"]["resource_feasible"] is False

def test_scenario_f_causal_change_is_qualified(session):
    phase=analyze(session,"Technical debt caused 2 outages and our largest customer is 35% of revenue.").analysis_outputs["phase2"]
    assert len(phase["causal_effects"])==2 and all(item["qualification"]=="may" for item in phase["causal_effects"])

def test_scenario_g_simple_question_bypasses_decision_engines():
    started=time.perf_counter();route=unified_aura_orchestrator.prepare("Explain what recurring revenue means.")
    assert not route.requires_decision_analysis and (time.perf_counter()-started)*1000<50

def test_scenario_h_state_evidence_remains_in_authenticated_scope(session):
    state=analyze(session,SCENARIO_B)
    assert all(item.organization_id in {None,1} and item.workspace_id in {None,1} for item in state.evidence)
    assert state.request.user_id==state.request.organization_id==state.request.workspace_id==1
