from app.intelligence_v2.clarification import ClarificationPlanner, information_sufficiency_service
from app.intelligence_v2.contracts import ClarificationState, DecisionRequest, DecisionType, GapImportance, InformationGap
from app.intelligence_v2.model_provider import MockModelProvider
from app.intelligence_v2.orchestrator import DecisionAnalysisOrchestrator
from app.intelligence_v2.service import decision_v2_service
from app.personal.safety import personal_safety_boundary
from tests.intelligence_v2.test_aevric_phase1 import STARTUP_CROSS_CONTEXT
from tests.intelligence_v2.test_decision_v2 import session
from tests.intelligence_v2.test_provider_efficiency_context import compact_response


EDUCATION_DECISION="""I am choosing among staying in my current role, studying independently, or entering a structured university degree or diploma program. My education goals are career growth, financial stability, and preserving time for existing responsibilities. The program funding is uncertain. Give me a clear recommendation, trade-offs, assumptions, uncertainty, what would change the recommendation, and a practical 12-month plan."""


def analyze(db,text,scope="personal",turns=None,session_id=None):
    return decision_v2_service.analyze_request(db=db,user_id=1,organization_id=1,workspace_id=1,user_query=text,decision_scope=scope,conversation_turns=turns or [],session_id=session_id)


def test_material_education_cost_unknown_reaches_provider_conditionally(session):
    state=analyze(session,EDUCATION_DECISION)
    provider=MockModelProvider(compact_response()); execution=DecisionAnalysisOrchestrator(provider).analyze(state)
    assert state.classification.decision_type is DecisionType.EDUCATION_DECISION
    assert state.analysis_status=="READY_FOR_ANALYSIS" and not state.clarification.questions and provider.calls==1
    assert "education_cost" in {gap.field for gap in state.information_gaps}
    assert all(state.analysis_outputs["phase2"]["requested_deliverables"][key] for key in ("recommendation","tradeoffs","assumptions","uncertainty","change_triggers"))
    assert state.analysis_outputs["phase2"]["plan"]["horizon_label"]=="12-Month"
    assert execution.status=="READY"


def test_startup_scenario_stays_ready_with_uncertainty(session):
    state=analyze(session,STARTUP_CROSS_CONTEXT,"auto")
    assert state.analysis_status=="READY_FOR_ANALYSIS" and not state.clarification.questions
    assert state.analysis_outputs["phase2"]["uncertainties"]


def test_ambiguous_objective_remains_decision_blocking(session):
    state=analyze(session,"I may leave my current job.")
    assert state.analysis_status=="CLARIFICATION_REQUIRED"
    assert state.clarification.blocking_gaps[0].field=="career_objective"


def test_material_modelable_constraint_is_retained_without_question(session):
    state=analyze(session,"I have $40,000 in savings and am deciding whether to buy a $20,000 vehicle now or wait. My goal is reliable transportation.")
    assert state.analysis_status=="READY_FOR_ANALYSIS" and not state.clarification.questions
    assert "financial_buffer" in {gap.field for gap in state.information_gaps}
    assert any("financial_buffer" in item for item in state.analysis_outputs["phase2"]["uncertainties"])


def test_non_material_unknown_does_not_trigger_clarification():
    gap=InformationGap("optional_detail","Helpful but peripheral.",GapImportance.LOW,"Minor precision only.",True,"What optional detail applies?")
    request=DecisionRequest(1,1,1,"Choose between two defined options using what is known.",missing_information=[gap])
    assessment=information_sufficiency_service.assess(request=request,gaps=[gap],conflicts=[])
    plan=ClarificationPlanner().plan(request=request,assessment=assessment,state=ClarificationState())
    assert assessment.can_proceed and not plan.should_clarify and not plan.questions


def test_missing_financial_resources_remains_blocking(session):
    state=analyze(session,"Help me decide whether a $25,000 car fits my budget.")
    assert state.analysis_status=="CLARIFICATION_REQUIRED"
    assert state.clarification.blocking_gaps[0].field=="available_resources"


def test_legitimate_answer_is_session_scoped_and_allows_analysis(session):
    state=analyze(session,"I may leave my current job.",session_id=77)
    question=state.clarification.questions[0]
    state=decision_v2_service.apply_clarification_answer(state=state,question=question,answer="I want to move into product leadership.")
    assert state.analysis_status=="READY_FOR_ANALYSIS"
    assert state.clarification_state.facts_added[-1].permission_scope=="session"


def test_new_conversation_does_not_inherit_old_goal(session):
    first=analyze(session,STARTUP_CROSS_CONTEXT,"auto",session_id=101)
    second=analyze(session,EDUCATION_DECISION,"personal",session_id=202)
    assert "startup into my primary career" in " ".join(first.analysis_outputs["phase2"]["goals"]).lower()
    assert "startup into my primary career" not in " ".join(second.analysis_outputs["phase2"]["goals"]).lower()


def test_existing_safety_boundary_precedes_decision_clarification():
    result=personal_safety_boundary.evaluate("I want to hurt myself.")
    assert result is not None and result.mode.startswith("SAFETY_")
