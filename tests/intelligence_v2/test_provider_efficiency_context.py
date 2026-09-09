import json

from app.intelligence_v2.model_provider import InvalidModelResponseError, MockModelProvider, analysis_max_output_tokens, model_analysis_schema
from app.intelligence_v2.orchestrator import DecisionAnalysisOrchestrator, RETRY_COMPACTION_PROMPT
from app.intelligence_v2.service import decision_v2_service
from app.personal.ask import analysis_report
from tests.intelligence_v2.test_aevric_phase1 import STARTUP_CROSS_CONTEXT, SequenceProvider
from tests.intelligence_v2.test_decision_v2 import session
from tests.intelligence_v2.test_quality_pass import grounded_response


EDUCATION="I want to move into cybersecurity while preserving financial stability. Should I take a diploma or study independently? Give me the trade-offs, uncertainty, recommendation-change conditions, and a practical 12-month plan."


def state(db,text): return decision_v2_service.analyze_request(db=db,user_id=1,organization_id=1,workspace_id=1,user_query=text,decision_scope="auto",conversation_turns=[])

def compact_response():
    raw=grounded_response(); raw.pop("key_tradeoffs",None); raw.pop("evidence_ids",None)
    raw["alternatives"]=[{key:value for key,value in item.items() if key!="assumptions"} for item in raw["alternatives"]]
    return raw


def test_complex_package_excludes_deterministic_presentation_duplication(session):
    current=state(session,STARTUP_CROSS_CONTEXT); package=DecisionAnalysisOrchestrator().package(current)
    compact=package.context["decision_intelligence"]
    assert set(compact)<= {"goals","options","decision_drivers","uncertainties"}
    assert not ({"plan","self_evaluation","participation","resources","goal_tensions","world_state"}&compact.keys())
    assert len(json.dumps(package.context)) < len(json.dumps(current.analysis_outputs["phase2"]))


def test_compact_schema_removes_redundant_fields_and_bounds_output():
    schema=model_analysis_schema()
    assert not {"key_tradeoffs","evidence_ids"}&schema["properties"].keys()
    assert "assumptions" not in schema["properties"]["alternatives"]["items"]["properties"]
    assert analysis_max_output_tokens()==1800
    assert all("maxLength" in schema["properties"][key] for key in ("problem_summary","recommended_option","rationale"))
    assert all("maxLength" in schema["properties"][key]["items"] for key in ("risks","assumptions_used","unresolved_questions","recommendation_change_conditions"))


def test_startup_brief_preserves_model_reasoning_and_deterministic_quality(session):
    current=state(session,STARTUP_CROSS_CONTEXT); provider=MockModelProvider(compact_response()); execution=DecisionAnalysisOrchestrator(provider).analyze(current); brief,_=analysis_report(current,execution)
    assert execution.status=="READY" and provider.calls==1
    assert brief["recommendation"]["recommended_option"] and brief["analysis"] and brief["alternatives"]
    assert brief["goals"] and brief["decision_drivers"] and brief["decision_plan"]["horizon_days"]==90


def test_education_compact_contract_preserves_tradeoffs_uncertainty_and_change_conditions(session):
    current=state(session,EDUCATION); current=decision_v2_service.proceed_with_assumptions(current); raw=grounded_response(); raw.update({"problem_summary":"Choose an education route.","recommended_option":"Study independently first","rationale":"This is the more reversible route.","risks":["The learning outcome is uncertain"],"unresolved_questions":["Employer recognition is unknown"],"recommendation_change_conditions":["Verified diploma outcomes justify the commitment"]}); raw["alternatives"]=[{"option":"Study independently first","benefits":["More reversible"],"downsides":["Less structured"],"evidence_ids":["user-query"],"conditions_for_success":["Verify learning progress"]},{"option":"Take the diploma","benefits":["More structured"],"downsides":["Larger commitment"],"evidence_ids":["user-query"],"conditions_for_success":["Verify outcomes"]}]
    execution=DecisionAnalysisOrchestrator(MockModelProvider(raw)).analyze(current); brief,_=analysis_report(current,execution)
    assert execution.status=="READY" and len(brief["alternatives"])==2 and brief["unresolved_questions"] and brief["what_would_change_recommendation"]
    assert brief["decision_plan"]["horizon_label"]=="12-Month" and all(brief["completeness"].values())


def test_evidence_ids_are_derived_from_option_grounding(session):
    raw=compact_response()
    execution=DecisionAnalysisOrchestrator(MockModelProvider(raw)).analyze(state(session,STARTUP_CROSS_CONTEXT))
    assert execution.status=="READY" and execution.result.evidence_used==["user-query"]


def test_incomplete_output_gets_one_concise_bounded_recovery(session):
    provider=SequenceProvider([InvalidModelResponseError("private","incomplete_max_tokens",{}),compact_response()])
    execution=DecisionAnalysisOrchestrator(provider).analyze(state(session,STARTUP_CROSS_CONTEXT))
    assert execution.status=="READY" and len(provider.calls)==2 and RETRY_COMPACTION_PROMPT in provider.calls[1]["system"]
    assert provider.calls[1]["payload"]["context"]=={} and len(provider.calls[1]["payload"]["evidence"])<=6


def test_two_incomplete_outputs_stop_after_maximum_one_retry(session):
    error=InvalidModelResponseError("private","incomplete_max_tokens",{})
    provider=SequenceProvider([error,error]); execution=DecisionAnalysisOrchestrator(provider).analyze(state(session,STARTUP_CROSS_CONTEXT))
    assert execution.status=="PARTIAL" and len(provider.calls)==2 and execution.usage["retry_count"]==1


def test_new_decision_state_does_not_inherit_prior_conversation_goal(session):
    prior=[{"role":"user","content":STARTUP_CROSS_CONTEXT}]
    fresh=state(session,EDUCATION)
    continued=decision_v2_service.analyze_request(db=session,user_id=1,organization_id=1,workspace_id=1,user_query=EDUCATION,decision_scope="auto",conversation_turns=prior)
    old_goal="startup into my primary career"
    assert old_goal not in " ".join(fresh.analysis_outputs["phase2"]["goals"]).lower()
    assert old_goal in " ".join(continued.analysis_outputs["phase2"]["goals"]).lower()


def test_current_goal_evidence_remains_scoped_to_current_session(session):
    first=decision_v2_service.analyze_request(db=session,user_id=1,organization_id=1,workspace_id=1,user_query=STARTUP_CROSS_CONTEXT,session_id=101,decision_scope="auto")
    second=decision_v2_service.analyze_request(db=session,user_id=1,organization_id=1,workspace_id=1,user_query=EDUCATION,session_id=202,decision_scope="auto")
    assert all(item.provenance.get("session_id")==101 for item in first.evidence if item.permission_scope=="session")
    assert all(item.provenance.get("session_id")==202 for item in second.evidence if item.permission_scope=="session")
