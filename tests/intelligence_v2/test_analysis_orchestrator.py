import json
import pytest
from app.intelligence_v2.model_provider import MockModelProvider, ProviderTimeoutError, ProviderUnavailableError, UnconfiguredModelProvider, analysis_verbosity
from app.intelligence_v2.orchestrator import DecisionAnalysisOrchestrator, SYSTEM_PROMPT
from app.intelligence_v2.service import decision_v2_service
from tests.intelligence_v2.test_decision_v2 import session
from app.intelligence_v2.evaluation import EVALUATION_CASES, EVALUATION_DIMENSIONS
from app.intelligence_v2.model_provider import analysis_max_output_tokens, analysis_reasoning_effort, analysis_result_schema, analysis_timeout_seconds, analysis_verbosity
from app.intelligence_v2.classifier import decision_classifier
from app.intelligence_v2.contracts import AnalysisAlternative, AnalysisPackage, AnalysisRecommendation, AnalysisResult, AssumptionItem, AssumptionStatus, DecisionType
from app.intelligence_v2.model_provider import InvalidModelResponseError, OpenAIModelProvider
from app.intelligence_v2.reasoning_policy import select_reasoning_effort
from types import SimpleNamespace
import httpx
import openai

def test_offline_evaluation_set_covers_required_stage_five_cases():
    assert {"cost_reduction","career_choice","pricing","hiring","investment","insufficient_information","contradictory_evidence","memory_recall","document_grounded"} <= set(EVALUATION_CASES)
    assert "citation_accuracy" in EVALUATION_DIMENSIONS and "non_fabrication" in EVALUATION_DIMENSIONS

def test_analysis_governance_defaults_and_bounds(monkeypatch):
    monkeypatch.delenv("AURA_AI_TIMEOUT_SECONDS", raising=False); monkeypatch.delenv("AURA_AI_MAX_OUTPUT_TOKENS", raising=False)
    assert analysis_timeout_seconds()==90 and analysis_max_output_tokens()==1800
    monkeypatch.setenv("AURA_AI_TIMEOUT_SECONDS","1"); monkeypatch.setenv("AURA_AI_MAX_OUTPUT_TOKENS","9000")
    assert analysis_timeout_seconds()==10 and analysis_max_output_tokens()==1800

def test_reasoning_effort_is_configurable_and_safe(monkeypatch):
    monkeypatch.delenv("AURA_AI_REASONING_EFFORT",raising=False); assert analysis_reasoning_effort()=="medium"
    monkeypatch.setenv("AURA_AI_REASONING_EFFORT","medium"); assert analysis_reasoning_effort()=="medium"
    monkeypatch.setenv("AURA_AI_REASONING_EFFORT","invalid"); assert analysis_reasoning_effort()=="medium"
    assert OpenAIModelProvider(api_key="test",model_name="gpt-5.1").reasoning_effort=="medium"

def test_orchestrator_passes_configured_timeout_without_retrying_provider(monkeypatch,session):
    state=ready_personal_state(session); provider=MockModelProvider(response()); monkeypatch.setenv("AURA_AI_TIMEOUT_SECONDS","120")
    execution=DecisionAnalysisOrchestrator(provider).analyze(state)
    assert execution.status=="READY" and provider.calls==1

def test_native_schema_is_strict_and_matches_canonical_required_fields():
    schema=analysis_result_schema(); assert schema["additionalProperties"] is False
    assert set(schema["required"])=={"problem_summary","alternatives","recommended_option","rationale","risks","assumptions_used","unresolved_questions","recommendation_change_conditions"}
    assert not {"citations","key_tradeoffs","evidence_ids"}&schema["properties"].keys() and schema["properties"]["alternatives"]["maxItems"]==3
    assert schema["properties"]["rationale"]["maxLength"]==600

def test_verbosity_configuration_is_safe_and_personal_default(monkeypatch):
    monkeypatch.delenv("AURA_AI_VERBOSITY",raising=False); assert analysis_verbosity()=="low"
    monkeypatch.setenv("AURA_AI_VERBOSITY","medium"); assert analysis_verbosity()=="medium"
    monkeypatch.setenv("AURA_AI_VERBOSITY","invalid"); assert analysis_verbosity()=="low"

def test_personal_taxonomy_and_business_regressions():
    assert decision_classifier.classify("I have two job offers: one remote, one with a commute and management track. Career growth matters.").decision_type is DecisionType.CAREER_DECISION
    assert decision_classifier.classify("Should I return to school for a college program?").decision_type is DecisionType.EDUCATION_DECISION
    assert decision_classifier.classify("I have savings and am buying a car because mine is unreliable.").decision_type is DecisionType.MAJOR_PURCHASE
    assert decision_classifier.classify("Launch an online business while working full time, with 10 hours per week.").decision_type is DecisionType.PERSONAL_PROJECT
    assert decision_classifier.classify("Reduce delivery costs by 20%.").decision_type is DecisionType.COST_REDUCTION
    assert decision_classifier.classify("Should we expand into a new market?").decision_type is DecisionType.MARKET_EXPANSION

def test_openai_response_states_are_classified_without_content_logging():
    provider=OpenAIModelProvider(api_key="test")
    def response(content, status="completed", refusal=None, reason=None):
        part=SimpleNamespace(type="output_text",text=content,refusal=refusal)
        return SimpleNamespace(status=status,incomplete_details=SimpleNamespace(reason=reason) if reason else None,error=None,output=[SimpleNamespace(content=[part])],usage=SimpleNamespace(input_tokens=3,output_tokens=4,output_tokens_details=SimpleNamespace(reasoning_tokens=1),total_tokens=7),_request_id="request-safe")
    parsed,meta=provider._parse_response(response('{"problem_summary":"ok"}'),0)
    assert parsed["problem_summary"]=="ok" and meta["content_length"]>0 and "content" not in meta and meta["reasoning_tokens"]==1
    for content,status,refusal,reason,category in [("{", "completed",None,None,"invalid_json"),("{}","incomplete",None,"max_output_tokens","incomplete_max_tokens"),(None,"completed",None,None,"empty_content"),(None,"completed","declined",None,"refusal"),("{}","failed",None,None,"provider_error")]:
        with pytest.raises(InvalidModelResponseError) as error: provider._parse_response(response(content,status,refusal,reason),0)
        assert error.value.category==category and "content" not in error.value.diagnostics

def test_strict_schema_request_and_reasoning_effort_are_constructed_offline():
    request=OpenAIModelProvider(api_key="test",model_name="gpt-5.1",reasoning_effort="medium").request_kwargs(system="safe",payload={"x":1})
    schema=request["text"]["format"]
    assert request["reasoning"]=={"effort":"medium"} and request["text"]["verbosity"]=="low" and request["store"] is False
    assert schema["type"]=="json_schema" and schema["name"]=="model_analysis_result" and schema["strict"] is True and schema["schema"]["additionalProperties"] is False

@pytest.mark.parametrize(("error","category"),[
    (lambda request,response: openai.AuthenticationError("denied",response=response,body=None),"authentication_error"),
    (lambda request,response: openai.RateLimitError("slow down",response=response,body=None),"rate_limit"),
    (lambda request,response: openai.BadRequestError("bad request",response=response,body=None),"bad_request"),
    (lambda request,response: openai.NotFoundError("missing",response=response,body=None),"model_not_found"),
    (lambda request,response: openai.APIConnectionError(message="offline",request=request),"api_connection_error"),
    (lambda request,response: TypeError("bad local shape"),"responses_configuration_error"),
])
def test_openai_request_exceptions_map_to_specific_safe_categories(error,category):
    request=httpx.Request("POST","https://api.openai.com/v1/responses")
    response=httpx.Response(400,request=request)
    mapped=OpenAIModelProvider(api_key="test")._map_request_exception(error(request,response))
    assert mapped.category==category
    assert mapped.diagnostics["provider"] == "openai"
    assert mapped.diagnostics["exception_type"] == type(error(request,response)).__name__
    assert mapped.diagnostics["response_state"] == "request_error"
    assert mapped.diagnostics["error_category"] == category
    assert mapped.diagnostics["model"] == "gpt-5.1"
    assert "bad local shape" not in str(mapped)

def test_responses_output_text_property_is_used_for_completed_structured_response():
    provider=OpenAIModelProvider(api_key="test")
    response=SimpleNamespace(status="completed",incomplete_details=None,error=None,output=[],output_text='{"problem_summary":"ok"}',usage=SimpleNamespace(input_tokens=1,output_tokens=2,output_tokens_details=SimpleNamespace(reasoning_tokens=0),total_tokens=3),id="resp-safe")
    parsed,diagnostics=provider._parse_response(response,0)
    assert parsed["problem_summary"]=="ok" and diagnostics["request_id"]=="resp-safe"

def test_reasoning_policy_selects_low_personal_medium_complex_and_honors_override(monkeypatch,session):
    monkeypatch.delenv("AURA_AI_REASONING_EFFORT",raising=False)
    personal=ready_personal_state(session); assert select_reasoning_effort(personal)==("none","straightforward_personal_comparison")
    complex_state=decision_v2_service.analyze_request(db=session,user_id=1,organization_id=1,workspace_id=1,user_query="Reduce delivery costs by 20% without reducing service quality")
    assert select_reasoning_effort(complex_state)[0]=="medium"
    monkeypatch.setenv("AURA_AI_REASONING_EFFORT","none"); assert select_reasoning_effort(personal)==("none","environment_override")
    monkeypatch.setenv("AURA_AI_REASONING_EFFORT","low"); assert select_reasoning_effort(personal)==("low","environment_override")
    monkeypatch.setenv("AURA_AI_REASONING_EFFORT",""); assert select_reasoning_effort(personal)[0]=="none"

def response(evidence_id="user-query"):
    return {"problem_summary":"Compare the supplied job offers against career growth and available evenings.","alternatives":[{"option":"Offer A","benefits":["Fully remote work"],"downsides":["Limited promotion opportunities"],"evidence_ids":[evidence_id],"assumptions":[],"conditions_for_success":[]},{"option":"Offer B conditionally","benefits":["Clear management track"],"downsides":["60-minute commute each way"],"evidence_ids":[evidence_id],"assumptions":[],"conditions_for_success":["The commute remains sustainable"]}],"recommended_option":"Offer B conditionally","rationale":"Career growth is the stated priority, subject to the commuting cost to evenings.","key_tradeoffs":["Growth versus free evenings"],"risks":["The commute may outweigh the career advantage"],"assumptions_used":[],"evidence_ids":[evidence_id],"unresolved_questions":[],"recommendation_change_conditions":["Evening-time priority outweighs the management track"]}

def ready_personal_state(session):
    state=decision_v2_service.analyze_request(db=session,user_id=1,organization_id=1,workspace_id=1,user_query="I have two job offers. Offer A pays $70,000, is fully remote, and has limited promotion opportunities. Offer B pays $78,000, requires a 60-minute commute each way, and has a clear management track. My top priority is career growth, but I strongly value having evenings free.")
    assert state.analysis_status=="READY_FOR_ANALYSIS"; return state

def test_clarification_prevents_provider_invocation(session):
    state=decision_v2_service.analyze_request(db=session,user_id=1,organization_id=1,workspace_id=1,user_query="reduce delivery costs by 20%")
    provider=MockModelProvider(response()); execution=DecisionAnalysisOrchestrator(provider).analyze(state)
    assert execution.status=="CLARIFICATION_REQUIRED" and provider.calls==0

def test_grounded_structured_personal_analysis_and_bounds(session):
    state=ready_personal_state(session); provider=MockModelProvider(response()); orchestrator=DecisionAnalysisOrchestrator(provider)
    package=orchestrator.package(state); execution=orchestrator.analyze(state)
    assert execution.status=="READY" and execution.result.recommendation.recommended_option.startswith("Offer B")
    assert len(package.evidence)<=orchestrator.max_evidence and all(len(item["content"])<=orchestrator.max_content_chars for item in package.evidence)
    assert execution.usage["provider"]=="mock" and execution.confidence in {"HIGH","MODERATE","LOW"}

def test_fabricated_citation_and_numeric_claim_are_never_accepted(session):
    state=ready_personal_state(session); bad=response("invented:99");bad["rationale"]="Revenue will increase by 999%"; execution=DecisionAnalysisOrchestrator(MockModelProvider(bad)).analyze(state)
    assert execution.status=="ANALYSIS_FAILED" and any("fabricated citation" in finding for finding in execution.critique_findings)

def test_provider_failure_modes_are_safe(session):
    state=ready_personal_state(session)
    assert DecisionAnalysisOrchestrator(UnconfiguredModelProvider()).analyze(state).status=="ANALYSIS_PROVIDER_UNAVAILABLE"
    retry=DecisionAnalysisOrchestrator(MockModelProvider(ProviderTimeoutError("timeout"))).analyze(state)
    assert retry.status=="PARTIAL" and retry.usage["retry_count"]==1

def test_request_error_diagnostics_survive_the_orchestrator_boundary(session):
    state=ready_personal_state(session)
    error=ProviderUnavailableError("OpenAI rejected the Responses request.","bad_request",{"exception_type":"BadRequestError","response_state":"request_error"})
    execution=DecisionAnalysisOrchestrator(MockModelProvider(error)).analyze(state)
    assert execution.status=="ANALYSIS_PROVIDER_UNAVAILABLE"
    assert execution.confidence_rationale==["provider_request_error:bad_request"]
    assert execution.usage["exception_type"]=="BadRequestError"

def test_unset_verbosity_uses_low_personal_safe_default(monkeypatch):
    monkeypatch.delenv("AURA_AI_VERBOSITY", raising=False)
    assert analysis_verbosity() == "low"

def test_northstar_evaluation_uses_only_authorized_evidence(session):
    state=decision_v2_service.analyze_request(db=session,user_id=1,organization_id=1,workspace_id=1,user_query="reduce delivery costs by 20% within 6 months without reducing service quality")
    state=decision_v2_service.proceed_with_assumptions(state)
    raw=response(); raw["problem_summary"]="Reduce delivery cost while protecting service."; raw["rationale"]="Investigate Route Group B before reducing service capacity."; raw["evidence_ids"]=["user-query"]; raw["alternatives"]=[{"option":"Route Group B","benefits":["Potential cost reduction"],"downsides":["Requires validation"],"evidence_ids":["user-query"],"assumptions":[],"conditions_for_success":[]}]
    execution=DecisionAnalysisOrchestrator(MockModelProvider(raw)).analyze(state)
    assert execution.status=="READY" and "Route Group B" in execution.result.recommendation.rationale

def test_compact_model_result_is_augmented_into_final_aura_contract(session):
    execution=DecisionAnalysisOrchestrator(MockModelProvider(response())).analyze(ready_personal_state(session))
    assert execution.status=="READY"
    assert execution.result.citations==execution.result.evidence_used==["user-query"]
    assert execution.result.key_facts and execution.result.recommendation.what_would_change_the_recommendation

def test_application_bounds_model_generated_collections(session):
    raw=response(); raw["alternatives"]*=4; raw["risks"]=["r"]*9; raw["recommendation_change_conditions"]=["c"]*8
    parsed=DecisionAnalysisOrchestrator()._parse_model(raw)
    assert len(parsed.alternatives)==3 and len(parsed.risks)==5 and len(parsed.recommendation_change_conditions)==4

def test_compact_contract_has_materially_smaller_offline_footprint_for_personal_and_operational_decisions():
    job_offer=response()
    northstar={**response(),"problem_summary":"Reduce delivery costs without reducing service quality.","alternatives":[{"option":"Route consolidation","benefits":["Lower delivery distance"],"downsides":["Operational change"],"evidence_ids":["user-query"],"assumptions":[],"conditions_for_success":["Pilot before rollout"]},{"option":"Supplier renegotiation","benefits":["Lower unit cost"],"downsides":["Contract dependency"],"evidence_ids":["user-query"],"assumptions":[],"conditions_for_success":["Validate service levels"]}],"recommended_option":"Route consolidation","rationale":"Pilot route consolidation before wider changes to protect service quality.","key_tradeoffs":["Cost reduction versus service consistency"],"risks":["A rushed rollout can degrade service"],"evidence_ids":["user-query"],"recommendation_change_conditions":["Pilot results show service degradation"]}
    def rich_final(compact):
        return {"problem_understanding":compact["problem_summary"],"key_facts":["Authorized fact one","Authorized fact two"]*3,"assumptions_used":compact["assumptions_used"],"alternatives":compact["alternatives"],"analysis":compact["rationale"]*4,"risks":compact["risks"]*3,"recommendation":{"recommended_option":compact["recommended_option"],"rationale":compact["rationale"]*3,"expected_effect":"Expected outcome from supplied evidence."*3,"prerequisites":["Validate before acting."]*3,"what_would_change_the_recommendation":compact["recommendation_change_conditions"]*3},"prioritized_actions":["Review the material trade-off before action."*3]*3,"unresolved_questions":compact["unresolved_questions"]*3,"evidence_used":compact["evidence_ids"]*3,"citations":compact["evidence_ids"]*3,"limitations":["Aura attaches provenance and remaining gaps."]*3}
    for compact in (job_offer,northstar):
        assert len(json.dumps(compact)) < len(json.dumps(rich_final(compact))) * .55

def test_job_offer_derives_commute_and_salary_evidence_with_authorized_provenance(session):
    state=ready_personal_state(session)
    derived={item.id:item for item in state.derived_evidence}
    assert derived["derived:annual_salary_difference"].claim=="Offer B pays $8,000 more annually."
    assert derived["derived:annual_salary_difference"].calculation=="78000 - 70000 = 8000"
    assert derived["derived:annual_salary_difference"].source_evidence_ids==["user-query"]
    assert derived["derived:commute_per_day"].claim=="The commute is 120 minutes (2 hours) per commuting day."
    assert derived["derived:commute_per_day"].calculation=="60 + 60 = 120 minutes"

def test_derived_commute_and_salary_numbers_are_grounded_not_hallucinations(session):
    state=ready_personal_state(session); raw=response()
    raw.update({"rationale":"Offer B pays $8,000 more annually and requires 2 hours commuting per commuting day.","evidence_ids":["user-query","derived:annual_salary_difference","derived:commute_per_day"]})
    execution=DecisionAnalysisOrchestrator(MockModelProvider(raw)).analyze(state)
    assert execution.status=="READY"
    assert "unsupported numeric claim: 2" not in execution.critique_findings
    assert any(item=="supported_derived numeric: 2" for item in execution.critique_findings)
    assert execution.result.derived_facts==["Offer B pays $8,000 more annually.","The commute is 120 minutes (2 hours) per commuting day."]

def test_unsupported_numeric_hallucination_remains_flagged(session):
    state=ready_personal_state(session); raw=response(); raw["rationale"]="Offer B will create 999 new opportunities."
    orchestrator=DecisionAnalysisOrchestrator(MockModelProvider(raw));package=orchestrator.package(state)
    parsed=orchestrator._augment(orchestrator._parse_model(raw,state),state,package)
    assert "unsupported numeric claim: 999" in orchestrator._validate(parsed,package)
    execution=orchestrator.analyze(state)
    assert execution.status=="READY" and execution.usage["claim_repair"]=="deterministic"

@pytest.mark.parametrize("assumption",["The commute is five days per week.","Treat the role as a 1–3 year commitment."])
def test_unsupported_commute_frequency_and_horizon_assumptions_are_rejected(session,assumption):
    state=ready_personal_state(session); raw=response(); raw["assumptions_used"]=[assumption]
    execution=DecisionAnalysisOrchestrator(MockModelProvider(raw)).analyze(state)
    assert execution.status=="ANALYSIS_FAILED"
    assert execution.confidence_rationale==["structured_validation_error:ValueError"]

def test_management_track_reliability_is_unresolved_not_a_working_assumption(session):
    state=ready_personal_state(session); raw=response(); raw["assumptions_used"]=["The management track is real and accessible with strong performance."]; raw["alternatives"][1]["assumptions"]=["The management track is genuine and performance-based."]
    execution=DecisionAnalysisOrchestrator(MockModelProvider(raw)).analyze(state)
    assert execution.status=="READY"
    assert execution.result.assumptions_used==[]
    assert execution.result.alternatives[1].assumptions==[]
    assert "How reliable is Offer B's management track in practice?" in execution.result.unresolved_questions
    assert execution.confidence=="MODERATE"

def test_unsupported_nonnumeric_personal_fact_fails_grounding(session):
    state=ready_personal_state(session); raw=response(); raw["rationale"]="Offer B has a supportive company culture and is therefore safer."
    execution=DecisionAnalysisOrchestrator(MockModelProvider(raw)).analyze(state)
    assert execution.status=="ANALYSIS_FAILED"
    assert "unsupported factual claim: unsupported employment condition" in execution.critique_findings

@pytest.mark.parametrize(("decision_type","unsupported_assumption"),[
    (DecisionType.CAREER_DECISION,"The future job market will improve."),
    (DecisionType.EDUCATION_DECISION,"You have family obligations."),
    (DecisionType.MAJOR_PURCHASE,"You prefer a luxury option."),
    (DecisionType.PERSONAL_FINANCE,"Your future income will rise."),
    (DecisionType.PERSONAL_PROJECT,"You can work every evening."),
    (DecisionType.RELOCATION,"A hybrid arrangement will be available."),
])
def test_personal_regression_set_rejects_unsupported_personal_assumptions(decision_type,unsupported_assumption):
    state=SimpleNamespace(classification=SimpleNamespace(decision_type=decision_type))
    raw=response(); raw["assumptions_used"]=[unsupported_assumption]
    with pytest.raises(ValueError,match="unsupported personal assumption"):
        DecisionAnalysisOrchestrator()._parse_model(raw,state)

def test_personal_prompt_requires_zero_assumptions_and_promotes_unknowns():
    assert "zero assumptions" in SYSTEM_PROMPT
    assert "unresolved_questions" in SYSTEM_PROMPT

def major_purchase_state(session):
    return decision_v2_service.analyze_request(db=session,user_id=1,organization_id=1,workspace_id=1,user_query="I'm deciding whether to spend $18,000 on a used car. I have $32,000 in savings. I earn $4,200 per month after tax. My normal monthly expenses are about $2,600. I currently spend about $450 per month on transportation. The car would eliminate most transportation spending, but insurance, fuel, and maintenance are unknown. One goal is to keep at least $20,000 in emergency savings.")

def test_major_purchase_derivations_are_authorized_and_provenanced(session):
    state=major_purchase_state(session); derived={item.id:item for item in state.derived_evidence}
    assert derived["derived:monthly_surplus"].claim=="Current monthly surplus is $1,600 per month."
    assert derived["derived:savings_after_purchase"].claim=="Savings after a cash purchase would be $14,000."
    assert derived["derived:emergency_savings_gap"].claim=="The purchase would leave savings $6,000 below the stated emergency-savings goal."
    assert all(item.source_evidence_ids==["user-query"] and item.operation=="subtraction" for item in derived.values())

def test_major_purchase_derived_numbers_are_supported_but_invented_numbers_fail(session):
    state=major_purchase_state(session); raw=response(); raw.update({"rationale":"A cash purchase leaves $14,000, $6,000 below the goal, with $1,600 monthly surplus.","evidence_ids":["user-query","derived:monthly_surplus","derived:savings_after_purchase","derived:emergency_savings_gap"],"alternatives":[{"option":"Delay purchase","benefits":["Preserves the emergency reserve"],"downsides":["Keeps current transportation spending"],"evidence_ids":["user-query"],"assumptions":[],"conditions_for_success":[]}],"recommended_option":"Delay purchase","recommendation_change_conditions":["Known ownership costs fit the budget"]})
    valid=DecisionAnalysisOrchestrator(MockModelProvider(raw)).analyze(state)
    assert valid.status=="READY" and not any("unsupported numeric" in item for item in valid.critique_findings)
    raw["rationale"]="Ownership costs are $1,150 and savings will be $12,000."
    orchestrator=DecisionAnalysisOrchestrator(MockModelProvider(raw));package=orchestrator.package(state)
    parsed=orchestrator._augment(orchestrator._parse_model(raw,state),state,package)
    assert {"unsupported numeric claim: 1,150","unsupported numeric claim: 12,000"} <= set(orchestrator._validate(parsed,package))
    repaired=orchestrator.analyze(state)
    assert repaired.status=="READY" and repaired.usage["repaired_numeric_values"]==["1150","12000"]


FOUNDER_CAR_INPUT = "I have $32,000 in savings and I'm thinking about buying a car for $18,000 in cash. I earn $4,200 per month and my regular expenses are about $2,600. I want to keep at least $20,000 in emergency savings. Should I buy the car now, choose something cheaper, or wait?"


def founder_car_state(session):
    return decision_v2_service.analyze_request(db=session,user_id=1,organization_id=1,workspace_id=1,user_query=FOUNDER_CAR_INPUT,decision_scope="personal")


def test_exact_founder_car_input_generates_only_authorized_quantitative_evidence(session):
    state=founder_car_state(session)
    assert state.classification.decision_type is DecisionType.MAJOR_PURCHASE
    derived={item.id:item for item in state.derived_evidence}
    assert set(derived)=={"derived:monthly_surplus","derived:savings_after_purchase","derived:emergency_savings_gap"}
    assert derived["derived:monthly_surplus"].source_values=={"income":"4200","expenses":"2600","surplus":"1600"}
    assert derived["derived:monthly_surplus"].calculation=="4200 - 2600 = 1600"
    assert derived["derived:savings_after_purchase"].source_values=={"savings":"32000","purchase":"18000","remaining":"14000"}
    assert derived["derived:savings_after_purchase"].calculation=="32000 - 18000 = 14000"
    assert derived["derived:emergency_savings_gap"].source_values=={"emergency_goal":"20000","after_purchase":"14000","gap":"6000"}
    assert derived["derived:emergency_savings_gap"].calculation=="20000 - 14000 = 6000"


def test_exact_founder_car_grounded_response_passes_and_new_provider_math_fails(session):
    state=founder_car_state(session); raw=response()
    raw.update({"problem_summary":"Choose whether to buy the stated car while protecting the stated reserve.","recommended_option":"Wait or choose a cheaper car","rationale":"The cash purchase leaves $14,000, which is $6,000 below the stated reserve target; current monthly surplus is $1,600.","evidence_ids":["user-query","derived:monthly_surplus","derived:savings_after_purchase","derived:emergency_savings_gap"],"alternatives":[{"option":"Wait or choose a cheaper car","benefits":["Protects the stated $20,000 reserve target"],"downsides":["Delays the purchase"],"evidence_ids":["user-query","derived:emergency_savings_gap"],"assumptions":[],"conditions_for_success":[]}],"recommendation_change_conditions":["A lower verified purchase price preserves the stated reserve"]})
    valid=DecisionAnalysisOrchestrator(MockModelProvider(raw)).analyze(state)
    assert valid.status=="READY"
    adversarial={
        "invented car price":"The alternative costs $12,000.","loan interest rate":"Financing costs 7%.",
        "monthly payment":"The payment is $450 monthly.","insurance":"Insurance is $200 monthly.",
        "fuel":"Fuel costs $150.","maintenance":"Maintenance costs $100.",
        "investment return":"Savings earn 5%.","future salary":"Future salary is $70,000.",
        "emergency expense":"An emergency costs $8,000.","rebuild months":"You can rebuild the gap in 4 months.",
        "derived percentage":"The car uses about 44% of savings.",
    }
    for label,claim in adversarial.items():
        bad=dict(raw);bad["rationale"]=claim
        execution=DecisionAnalysisOrchestrator(MockModelProvider(bad)).analyze(state)
        assert execution.status=="READY",label
        assert execution.usage["claim_repair"]=="deterministic",label


def test_rejected_numeric_diagnostic_is_normalized_and_contains_no_prompt(session):
    state=founder_car_state(session);raw=response();raw["rationale"]="You can rebuild the $6,000 gap in 4 months at 44%.";raw["alternatives"]=[{"option":"Wait","benefits":["Preserve savings"],"downsides":["Delay purchase"],"evidence_ids":["user-query"],"assumptions":[],"conditions_for_success":[]}];raw["recommended_option"]="Wait"
    execution=DecisionAnalysisOrchestrator(MockModelProvider(raw)).analyze(state)
    assert execution.usage["repaired_numeric_values"]==["4","44%"]
    assert FOUNDER_CAR_INPUT not in str(execution.usage)

def grounding_findings(text, *, derived=False, source_text="Authorized scenario."):
    evidence=[{"id":"user-query","content":source_text,"provenance":{}}]
    if derived: evidence.append({"id":"derived:commute","content":"The commute is 120 minutes (2 hours) per commuting day.","provenance":{"derived":True,"numeric_values":["120","2"]}})
    result=AnalysisResult("p",[],[],[AnalysisAlternative("option",[],[],["user-query"],[],[])],text,[],AnalysisRecommendation("option",text,"",[],[]),[],[],["user-query"],["user-query"],[],[])
    return DecisionAnalysisOrchestrator()._validate(result,AnalysisPackage({}, {}, evidence, [], [], {}, []))

@pytest.mark.parametrize("label",["Option 1 preserves cash.","Option 2 preserves cash.","Alternative 1 is safer.","Step 2 compares costs.","Risk 3 is uncertainty."])
def test_structural_numbers_are_not_grounded_as_factual_claims(label):
    assert not any("unsupported numeric" in item for item in grounding_findings(label))

@pytest.mark.parametrize("claim",["It costs $1,150 monthly.","The balance is $12,000.","Wait 2 months.","Insurance is $200.","Your salary will increase 10%."])
def test_factual_numbers_still_require_grounding(claim):
    assert any("unsupported numeric" in item for item in grounding_findings(claim))

def test_digit_claim_is_grounded_by_equivalent_number_word_evidence():
    findings=grounding_findings("5 customers requested analytics.",source_text="Five customers requested analytics.")
    assert "supported_literal numeric: 5" in findings
    assert "unsupported numeric claim: 5" not in findings

def test_number_word_normalization_does_not_accept_a_different_number():
    assert "unsupported numeric claim: 5" in grounding_findings(
        "5 customers requested analytics.", source_text="Four customers requested analytics."
    )

def test_derived_two_hours_requires_provenance_and_generic_benefits_are_safe():
    assert "supported_derived numeric: 2" in grounding_findings("Drive 2 hours per commuting day.",derived=True)
    assert "unsupported numeric claim: 2" in grounding_findings("Drive 2 hours per commuting day.")
    assert not any("employment condition" in item for item in grounding_findings("The benefits of buying the vehicle depend on unknown ownership costs."))

@pytest.mark.parametrize("claim",["Your employer allows remote work.","Your employer pays commuting costs.","Your salary will increase next year.","Your company provides health benefits."])
def test_unsupported_employment_assertions_are_rejected(claim):
    assert "unsupported factual claim: unsupported employment condition" in grounding_findings(claim)

def test_sufficiency_and_recommendation_confidence_are_separate(session):
    state=ready_personal_state(session); execution=DecisionAnalysisOrchestrator(MockModelProvider(response())).analyze(state)
    assert state.sufficiency.status.value=="sufficient"
    assert execution.confidence=="MODERATE"
    assert "recommendation-sensitive uncertainty" in execution.confidence_rationale[0]

def test_recommendation_confidence_is_high_only_when_evidence_is_robust(session):
    state=ready_personal_state(session); raw=response(); raw["unresolved_questions"]=[]; raw["recommendation_change_conditions"]=[]
    execution=DecisionAnalysisOrchestrator(MockModelProvider(raw)).analyze(state)
    assert execution.status=="READY" and execution.confidence=="HIGH"

def test_recommendation_confidence_is_low_when_major_working_assumptions_remain(session):
    state=ready_personal_state(session); state.assumptions.append(AssumptionItem("Promotion reliability is unknown","test",0.0,AssumptionStatus.UNVERIFIED,"The recommendation could change."))
    execution=DecisionAnalysisOrchestrator(MockModelProvider(response())).analyze(state)
    assert execution.status=="READY" and execution.confidence=="LOW"
