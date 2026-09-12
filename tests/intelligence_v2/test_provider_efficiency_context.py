import json

import pytest

from app.intelligence_v2.model_provider import InvalidModelResponseError, MockModelProvider, analysis_max_output_tokens, model_analysis_schema
from app.intelligence_v2.final_quality import FinalBriefQualityError, _clean_with_rule
from app.intelligence_v2.fact_extraction import extract_fact_ledger
from app.intelligence_v2.quality import requested_deliverables
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


def test_education_brief_repairs_presentation_leaks_without_losing_requested_plan(session, caplog):
    prompt=("I want to move into cybersecurity while preserving financial stability. "
            "I earn $72,000 and am choosing a diploma or independent study. "
            "Give me the trade-offs, uncertainty, recommendation-change conditions, "
            "and a plan for the next 12 months.")
    current=state(session,prompt)
    assert current.classification.decision_type.value=="education_decision" and not current.clarification.questions
    raw=grounded_response(); raw.update({"problem_summary":"Choose an education route.","recommended_option":"Study independently first","rationale":"It is reversible.","risks":["Employer recognition is uncertain","Explain the trade-offs and uncertainty","then doing a second,","someone who enjoys学习"],"unresolved_questions":["education_cost: Diploma tuition is unknown"],"recommendation_change_conditions":["Verified outcomes justify the diploma","If a low-cost opportunity becomes available, a"]})
    raw["alternatives"]=[{"option":"Study independently first","benefits":["user-query","More reversible"],"downsides":["Less structured"],"evidence_ids":["user-query"],"conditions_for_success":["Verify progress"]},{"option":"Take the diploma","benefits":["Structured instruction"],"downsides":["document:abc"],"evidence_ids":["user-query"],"conditions_for_success":["Verify outcomes"]}]
    provider=MockModelProvider(raw);execution=DecisionAnalysisOrchestrator(provider).analyze(current)
    brief,_=analysis_report(current,execution); rendered=json.dumps(brief,ensure_ascii=False)
    assert provider.calls==1 and execution.status=="READY"
    assert brief["recommendation"]["recommended_option"] and brief["recommendation"]["rationale"]
    assert any(item["benefits"] or item["downsides"] for item in brief["alternatives"])
    assert brief["decision_plan"]["horizon_label"]=="12-Month"
    display_tradeoffs=json.dumps([{"benefits":item["benefits"],"downsides":item["downsides"]} for item in brief["alternatives"]])
    assert "user-query" not in display_tradeoffs and "education_cost" not in rendered
    assert "Explain the trade-offs" not in rendered and "then doing a second" not in rendered and "low-cost opportunity becomes available, a" not in rendered and "学习" not in rendered
    assert prompt not in brief["evidence_quality"]["known"]
    assert all(len(item)<240 for item in brief["evidence_quality"]["known"])
    assert "startup" not in " ".join(brief["goals"]).lower()
    assert not execution.critique_findings
    assert "final_quality_stage=passed" in caplog.text


def test_requested_plan_is_specific_and_has_usable_language(session):
    current=state(session,"Our goals are preserve cash and launch a service. Our options are pilot or wait. Give us a 90-day plan.")
    plan=current.analysis_outputs["phase2"]["plan"];text=json.dumps(plan)
    assert plan["phases"] and ("pilot" in text.lower() or "launch a service" in text.lower())
    assert "terms and constraints that differ" not in text and "smallest reversible test supported" not in text and "update the decision" not in text
    assert "Check whether run" not in text and "Check whether update" not in text


def test_instruction_is_not_promoted_to_goal_risk_or_uncertainty(session):
    prompt="I want financial stability. Explain the trade-offs, assumptions, uncertainty, and what would change the recommendation."
    phase=state(session,prompt).analysis_outputs["phase2"];display=json.dumps({key:phase[key] for key in ("goals","risks","uncertainties")})
    assert "Explain the trade-offs" not in display


def test_known_uses_atomic_grounded_facts_and_qualitative_decision_state(session):
    prompt="I earn $72,000. My goal is to preserve stability. My options are change careers or remain employed."
    current=decision_v2_service.proceed_with_assumptions(state(session,prompt));execution=DecisionAnalysisOrchestrator(MockModelProvider(grounded_response())).analyze(current)
    brief,_=analysis_report(current,execution);known=brief["evidence_quality"]["known"]
    assert known and any(item.startswith(("Salary:","Goal:","Option:")) for item in known)
    assert prompt not in known and all("user-query" not in item and len(item)<240 for item in known)


@pytest.mark.parametrize(("text","expected"),[("Create a startup plan for the next 30 days.",(30,"days")),("Provide a roadmap over 90 days.",(90,"days")),("Create a plan across the next 6 months.",(6,"months")),("Give me a plan for the next 12 months.",(12,"months"))])
def test_alternate_plan_horizon_phrasing_is_detected(text,expected):
    horizon=requested_deliverables(text)["plan_horizon"]
    assert (horizon["value"],horizon["unit"])==expected


def test_unrequested_plan_remains_absent_for_education_decision(session):
    current=state(session,"Should I take a diploma or study independently?")
    assert current.analysis_outputs["phase2"]["plan"].get("phases") is None


def test_multilingual_content_is_preserved_when_present_in_user_source(session):
    current=decision_v2_service.proceed_with_assumptions(state(session,"我应该参加文凭课程还是独立学习? Compare the options."))
    raw=grounded_response();raw["risks"]=["学习进度可能不确定"]
    execution=DecisionAnalysisOrchestrator(MockModelProvider(raw)).analyze(current)
    brief,_=analysis_report(current,execution)
    assert "学习进度可能不确定" in brief["risks"]


@pytest.mark.parametrize(("recommendation","quality_rule"),[("Study independently, then doing a second,","dangling"),("Study independently while keeping open the later","dangling_english"),("Choose the reversible path without committing to another long, expensive degree right","subordinate_modifier"),("Focus more tightly on income-generating","trailing_modifier")])
def test_dangling_required_recommendation_fails_closed(session, caplog, recommendation, quality_rule):
    current=decision_v2_service.proceed_with_assumptions(state(session,EDUCATION))
    raw=grounded_response();raw["recommended_option"]=recommendation
    execution=DecisionAnalysisOrchestrator(MockModelProvider(raw)).analyze(current)
    with pytest.raises(FinalBriefQualityError) as captured:
        analysis_report(current,execution)
    assert captured.value.required_field=="recommended_option" and captured.value.quality_rule==quality_rule
    expected=f"final_quality_stage=failed failure_category=malformed_required_section required_field=recommended_option quality_rule={quality_rule}"
    assert expected in caplog.text and recommendation not in caplog.text


def test_required_rationale_diagnostic_identifies_field_without_content(session, caplog):
    current=decision_v2_service.proceed_with_assumptions(state(session,EDUCATION))
    raw=grounded_response();raw["rationale"]="Choose this route because"
    execution=DecisionAnalysisOrchestrator(MockModelProvider(raw)).analyze(current)
    with pytest.raises(FinalBriefQualityError) as captured:
        analysis_report(current,execution)
    assert captured.value.required_field=="rationale" and captured.value.quality_rule=="dangling"
    assert "required_field=rationale quality_rule=dangling" in caplog.text
    assert raw["rationale"] not in caplog.text


def test_malformed_requested_change_condition_fails_closed(session, caplog):
    current=decision_v2_service.proceed_with_assumptions(state(session,EDUCATION+" Explain what would change the recommendation."))
    raw=grounded_response();raw["recommendation_change_conditions"]=["Shift toward an additional full-"]
    execution=DecisionAnalysisOrchestrator(MockModelProvider(raw)).analyze(current)
    with pytest.raises(FinalBriefQualityError) as captured:
        analysis_report(current,execution)
    assert "missing_change_conditions" in captured.value.categories
    assert "Shift toward" not in caplog.text


@pytest.mark.parametrize("article",["a","A","an","An","the","The"])
def test_terminal_article_fragment_is_rejected_case_insensitively(article):
    text=f"A complete thought. {article}"
    clean,rule=_clean_with_rule(text,"An English decision request.",optional=False,reject_instructions=False)
    assert clean=="" and rule in {"sentence_fragment","dangling_english"}


@pytest.mark.parametrize("boundary",["-","‑","–","—"])
def test_truncated_terminal_boundary_is_rejected_before_cleaning(boundary):
    text=f"Shift toward an additional full{boundary}"
    assert _clean_with_rule(text,"An English decision request.",optional=False,reject_instructions=False)==("","trailing_boundary")


def test_valid_hyphenated_and_multilingual_prose_remain_supported():
    assert _clean_with_rule("Use a well-tested approach.","An English decision request.")[0]=="Use a well-tested approach."
    multilingual="学習進度はまだ不確実です"
    assert _clean_with_rule(multilingual,f"Compare the options in Japanese: {multilingual}")[0]==multilingual


@pytest.mark.parametrize(("prompt","expected"),[
    ("My options are finish my IT program and pursue a degree in economics or finance.",["finish my IT program and pursue a degree in economics or finance"]),
    ("I have three options: enter the workforce, build projects, or pursue a degree in economics or finance.",["enter the workforce","build projects","pursue a degree in economics or finance"]),
    ("I have three options: 1. Enter the workforce. 2. Build projects. 3. Pursue a degree.",["Enter the workforce","Build projects","Pursue a degree"]),
    ("My options are full-time or part-time study.",["full-time or part-time study"]),
])
def test_option_normalization_uses_structural_separators(prompt,expected):
    assert extract_fact_ledger(prompt)["options"]==expected


def test_internal_or_option_remains_one_option_through_phase2(session):
    prompt="My option is pursue another degree in economics or finance. Should I pursue it?"
    current=state(session,prompt)
    assert current.analysis_outputs["phase2"]["options"]==["pursue another degree in economics or finance"]


def test_equivalent_gap_unknowns_are_deduplicated_but_distinct_unknowns_remain(session):
    current=decision_v2_service.proceed_with_assumptions(state(session,EDUCATION))
    raw=grounded_response();raw["unresolved_questions"]=["How expensive would a second degree be and how would you fund it?","Would employers recognize independent study?"]
    execution=DecisionAnalysisOrchestrator(MockModelProvider(raw)).analyze(current)
    brief,_=analysis_report(current,execution)
    visible=[*brief["evidence_quality"]["unknown"],*brief["unresolved_questions"],*brief["uncertainties"]]
    cost_items=[item for item in visible if any(word in item.lower() for word in ("expensive","cost","tuition","fund"))]
    assert len(cost_items)==1 and any("employer" in item.lower() for item in visible)
    assert "education_cost" not in json.dumps(brief)


def test_production_shaped_education_brief_has_integrity_without_provider_network(session):
    prompt=("I'm 20 years old and currently studying Information Technology. Education genuinely matters to me. "
            "I have limited financial resources and my time is a material constraint. My goal is to build companies eventually. "
            "Three paths: enter the workforce, build practical projects, or pursue another degree. "
            "Explain the trade-offs, assumptions, uncertainty, and what would change the recommendation, and give me a practical plan for the next 12 months.")
    current=state(session,prompt);raw=grounded_response();raw.update({"problem_summary":"Choose a grounded next path.","recommended_option":"Enter the workforce while testing practical projects","rationale":"This preserves flexibility while building relevant experience.","unresolved_questions":["Exact resources available for each path"],"recommendation_change_conditions":["Verified constraints make another path materially stronger"]})
    raw["alternatives"]=[{"option":"Enter the workforce","benefits":["Build practical experience"],"downsides":["Less formal study"],"evidence_ids":["user-query"],"conditions_for_success":["Confirm suitable roles"]},{"option":"Build practical projects","benefits":["Test company-building skills"],"downsides":["Income may remain uncertain"],"evidence_ids":["user-query"],"conditions_for_success":["Define a reversible project"]},{"option":"Pursue another degree","benefits":["Continue formal education"],"downsides":["Uses limited time and resources"],"evidence_ids":["user-query"],"conditions_for_success":["Confirm feasibility"]}]
    provider=MockModelProvider(raw);execution=DecisionAnalysisOrchestrator(provider).analyze(current);brief,_=analysis_report(current,execution);rendered=json.dumps(brief,ensure_ascii=False)
    known=brief["evidence_quality"]["known"];plan=brief["decision_plan"];actions=" ".join(action for phase in plan["phases"] for action in phase["actions"])
    assert provider.calls==1 and execution.status=="READY" and brief["recommendation"]["recommended_option"] in actions
    assert [phase["phase"] for phase in plan["phases"]]==["Months 1–3","Months 4–6","Months 7–9","Months 10–12"]
    assert all(phase["checkpoint"] and phase["reassessment_trigger"] for phase in plan["phases"])
    assert len({phase["reassessment_trigger"] for phase in plan["phases"]})==4
    assert sum(phase["reassessment_trigger"]==raw["recommendation_change_conditions"][0] for phase in plan["phases"])==1
    assert len(current.analysis_outputs["phase2"]["options"])==3
    assert any(item.startswith("Age:") for item in known) and any(item.startswith("Current status:") for item in known)
    assert any(item.startswith("Option:") for item in known) and not all(item.startswith("Goal:") for item in known)
    leaks=[token for token in ("education_cost","user-query","Check whether clarify","Check whether run","Check whether update") if token in rendered]
    assert prompt not in known and not leaks,leaks
    assert rendered.count("Cost and financial runway affect feasibility")==0
    assert brief["next_move"] and not brief["next_move"].startswith("Check whether")


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
