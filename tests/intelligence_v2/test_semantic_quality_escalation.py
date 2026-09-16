import json
import logging

import pytest

from app.intelligence_v2.final_quality import FinalBriefQualityError, SemanticRouting, route_semantic_ambiguity
from app.intelligence_v2.model_provider import InvalidModelResponseError, MockModelProvider, ProviderTimeoutError, ProviderUnavailableError, SEMANTIC_QUALITY_OUTPUT_TOKENS, semantic_quality_schema
from app.intelligence_v2.orchestrator import DecisionAnalysisOrchestrator
from app.intelligence_v2.service import decision_v2_service
from app.personal.ask import analysis_report
from app.api import personal_ask_routes as routes
from tests.api.test_personal_ask_api import _client, _identity, _model_response
from tests.intelligence_v2.test_decision_v2 import session
from tests.intelligence_v2.test_provider_efficiency_context import EDUCATION, SequenceProvider, state
from tests.intelligence_v2.test_quality_pass import grounded_response


class RecordingClassifier:
    def __init__(self, result="complete", *, overrides=None, error=None, raw=None):
        self.result=result;self.overrides=overrides or {};self.error=error;self.raw=raw;self.calls=[]
    def __call__(self,candidates):
        self.calls.append(candidates)
        if self.error:raise self.error
        if self.raw is not None:return self.raw,{"latency_ms":4,"input_tokens":23,"output_tokens":11,"total_tokens":34}
        results=[]
        for candidate in candidates:
            value=self.overrides.get((candidate["field_id"],candidate["item_index"]),self.result)
            results.append({"field_id":candidate["field_id"],"item_index":candidate["item_index"],"result":value,"reason":"truncated_phrase" if value=="incomplete" else "context_insufficient"})
        return {"results":results},{"latency_ms":4,"input_tokens":23,"output_tokens":11,"total_tokens":34}


def execution_and_state(db,raw=None,prompt=EDUCATION,provider=None):
    current=decision_v2_service.proceed_with_assumptions(state(db,prompt))
    provider=provider or MockModelProvider(raw or grounded_response())
    return current,provider,DecisionAnalysisOrchestrator(provider).analyze(current)


def boundary_raw():
    raw=grounded_response();raw["rationale"]="This preserves flexibility while evidence develops—";return raw


def clustered_raw():
    raw=grounded_response();raw["risks"]=["Choose A or","Keep a balanced approach"]
    raw["recommendation_change_conditions"]=["If circumstances change, then","Verified outcomes favor another path"]
    return raw


def test_normal_complete_brief_does_not_escalate_and_uses_one_call(session):
    current,provider,execution=execution_and_state(session)
    classifier=RecordingClassifier();brief,_=analysis_report(current,execution,semantic_classifier=classifier)
    assert provider.calls==1 and classifier.calls==[] and brief["telemetry"]["provider_calls"]==1
    assert brief["telemetry"]["semantic_quality"]["stage"]=="skipped_complete"


def test_boundary_recovery_routes_ambiguous_and_batches_one_classifier_call(session):
    current,provider,execution=execution_and_state(session,boundary_raw())
    classifier=RecordingClassifier();brief,_=analysis_report(current,execution,semantic_classifier=classifier)
    assert provider.calls==1 and len(classifier.calls)==1 and brief["telemetry"]["provider_calls"]==2
    assert brief["telemetry"]["semantic_quality"]["triggers"]==["boundary_recovery"]
    assert {item["field_id"] for item in classifier.calls[0]}=={"rationale"}


def test_recovery_cluster_routes_all_canonical_provider_candidates(session):
    current,_,execution=execution_and_state(session,clustered_raw());classifier=RecordingClassifier()
    brief,_=analysis_report(current,execution,semantic_classifier=classifier)
    assert "recovery_cluster" in brief["telemetry"]["semantic_quality"]["triggers"]
    assert len(classifier.calls)==1 and len(classifier.calls[0])>5


def test_output_headroom_and_length_proximity_are_objective_router_signals():
    response={"problem_understanding":"P","alternatives":[],"risks":[],"unresolved_questions":[],"recommendation":{"recommended_option":"R","rationale":"x"*540,"what_would_change_the_recommendation":[]}}
    routing,candidates,triggers=route_semantic_ambiguity(response,[],{"output_tokens":1620})
    assert routing is SemanticRouting.AMBIGUOUS
    assert {"output_headroom","field_length_proximity"}<=set(triggers)
    assert any(item["field_id"]=="rationale" for item in candidates)


def test_one_optional_degradation_alone_does_not_trigger_cluster():
    response={"problem_understanding":"P","alternatives":[],"risks":[],"unresolved_questions":[],"recommendation":{"recommended_option":"R","rationale":"Complete rationale","what_would_change_the_recommendation":[]}}
    routing,candidates,triggers=route_semantic_ambiguity(response,[{"action":"degraded","field":"risk","rule":"dangling"}],{})
    assert routing is SemanticRouting.COMPLETE and candidates==[] and triggers==[]


def test_four_production_fragments_are_batched_without_lexical_rules(session):
    love="Immediately starting another full degree would directly satisfy the love"
    full="Keeps optionality to learn economics, finance, history, philosophy, international affairs, and business through self-study and shorter, flexible programs instead of a long new full"
    aligned="If, during early work experience, you find that your job heavily underuses your abilities and offers little learning, and a targeted degree would clearly open better, more aligned"
    reconsider="If you try self-directed learning for an extended period and find you cannot sustain depth or consistency despite adjustments, a structured degree program might be worth reconsider"
    raw=grounded_response();raw["rationale"]=love+"—"
    raw["alternatives"][0]["benefits"]=[full,"Choose A or"]
    raw["recommendation_change_conditions"]=[aligned,reconsider]
    current,_,execution=execution_and_state(session,raw);classifier=RecordingClassifier(result="uncertain")
    brief,_=analysis_report(current,execution,semantic_classifier=classifier)
    submitted={item["text"] for item in classifier.calls[0]}
    assert {love,full,aligned,reconsider}<=submitted
    assert all(fragment in json.dumps(brief,ensure_ascii=False) for fragment in (love,full,aligned,reconsider))


def test_valid_unusual_prose_and_uncertain_result_are_retained(session):
    raw=boundary_raw();raw["rationale"]="Learning by doing—"
    current,_,execution=execution_and_state(session,raw);classifier=RecordingClassifier(result="uncertain")
    brief,_=analysis_report(current,execution,semantic_classifier=classifier)
    assert brief["recommendation"]["rationale"]=="Learning by doing"


def test_multilingual_candidate_can_be_routed_without_content_interpretation():
    text="学習の選択肢はまだ有効です"
    response={"problem_understanding":text,"alternatives":[],"risks":[],"unresolved_questions":[],"recommendation":{"recommended_option":text,"rationale":text,"what_would_change_the_recommendation":[]}}
    routing,candidates,triggers=route_semantic_ambiguity(response,[{"action":"repaired","field":"rationale","rule":"trailing_boundary"}],{})
    assert routing is SemanticRouting.AMBIGUOUS and triggers==["boundary_recovery"]
    assert candidates[0]["text"]==text and candidates[0]["field_id"]=="rationale"


def test_optional_incomplete_condition_is_removed_before_plan_and_alias_projection(session):
    raw=clustered_raw();target="Verified outcomes favor another path"
    current,_,execution=execution_and_state(session,raw)
    classifier=RecordingClassifier(overrides={("recommendation_change_condition",0):"incomplete"})
    brief,_=analysis_report(current,execution,semantic_classifier=classifier);serialized=json.dumps(brief,ensure_ascii=False)
    assert target not in serialized
    assert brief["what_would_change_recommendation"]==brief["recommendation"]["what_would_change_the_recommendation"]
    assert target not in json.dumps(brief["decision_plan"],ensure_ascii=False) and brief["next_move"]!=target


def test_optional_incomplete_benefit_degrades_only_that_item(session):
    raw=clustered_raw();target=raw["alternatives"][0]["benefits"][0]
    current,_,execution=execution_and_state(session,raw);classifier=RecordingClassifier(overrides={("alternative_benefit",0):"incomplete"})
    brief,_=analysis_report(current,execution,semantic_classifier=classifier)
    assert target not in brief["alternatives"][0]["benefits"] and len(brief["alternatives"])==len(raw["alternatives"])


def test_required_incomplete_uses_existing_quality_error(session):
    current,_,execution=execution_and_state(session,boundary_raw());classifier=RecordingClassifier(result="incomplete")
    with pytest.raises(FinalBriefQualityError) as captured:analysis_report(current,execution,semantic_classifier=classifier)
    assert captured.value.categories==("semantic_incomplete_required",) and captured.value.required_field=="rationale"


@pytest.mark.parametrize("error,stage",[(ProviderTimeoutError("private","timeout"),"timeout"),(ProviderUnavailableError("private","provider_unavailable"),"unavailable")])
def test_classifier_transport_failure_preserves_deterministic_content(session,error,stage):
    current,_,execution=execution_and_state(session,boundary_raw());classifier=RecordingClassifier(error=error)
    brief,_=analysis_report(current,execution,semantic_classifier=classifier)
    assert brief["recommendation"]["rationale"]=="This preserves flexibility while evidence develops"
    assert brief["telemetry"]["semantic_quality"]["stage"]==stage


def test_invalid_classifier_schema_preserves_deterministic_content(session):
    current,_,execution=execution_and_state(session,boundary_raw());classifier=RecordingClassifier(raw={"results":[]})
    brief,_=analysis_report(current,execution,semantic_classifier=classifier)
    assert brief["recommendation"]["rationale"] and brief["telemetry"]["semantic_quality"]["stage"]=="invalid_schema"


def test_deterministic_hard_failure_never_calls_classifier(session):
    raw=grounded_response();raw["rationale"]="Choose this because"
    current,_,execution=execution_and_state(session,raw);classifier=RecordingClassifier()
    with pytest.raises(FinalBriefQualityError):analysis_report(current,execution,semantic_classifier=classifier)
    assert classifier.calls==[]


def test_generation_retry_consumes_call_two_and_semantic_classifier_is_skipped(session,caplog):
    provider=SequenceProvider([InvalidModelResponseError("private","incomplete_max_tokens",{}),boundary_raw()])
    current,provider,execution=execution_and_state(session,provider=provider);classifier=RecordingClassifier()
    caplog.set_level(logging.WARNING,logger="uvicorn.error")
    brief,_=analysis_report(current,execution,semantic_classifier=classifier)
    assert len(provider.calls)==2 and classifier.calls==[] and brief["telemetry"]["provider_calls"]==2
    assert "semantic_quality_stage=skipped semantic_quality_trigger=call_budget_exhausted semantic_quality_action=skipped_call_budget" in caplog.text


def test_classifier_payload_is_minimal_and_excludes_request_and_identity(session):
    current,_,execution=execution_and_state(session,boundary_raw());classifier=RecordingClassifier()
    analysis_report(current,execution,semantic_classifier=classifier)
    payload=classifier.calls[0];serialized=json.dumps(payload)
    assert all(set(item)=={"field_id","item_index","text"} for item in payload)
    assert current.request.user_query not in serialized
    assert not any(token in serialized for token in ("user_id","session_id","workspace_id","organization_id","evidence_ids","source_metadata"))


def test_semantic_logs_contain_only_safe_enums(session,caplog):
    secret="PRIVATE-CANDIDATE-DO-NOT-LOG";raw=grounded_response();raw["rationale"]=secret+"—"
    current,_,execution=execution_and_state(session,raw);classifier=RecordingClassifier(result="incomplete")
    caplog.set_level(logging.WARNING,logger="uvicorn.error")
    with pytest.raises(FinalBriefQualityError):analysis_report(current,execution,semantic_classifier=classifier)
    semantic_logs="\n".join(record.message for record in caplog.records if "semantic_quality_" in record.message)
    assert secret not in semantic_logs and "semantic_quality_result=incomplete" in semantic_logs


def test_classifier_schema_and_budget_are_strict_and_small():
    schema=semantic_quality_schema();item=schema["properties"]["results"]["items"]
    assert schema["additionalProperties"] is False and item["additionalProperties"] is False
    assert set(item["properties"]["result"]["enum"])=={"complete","incomplete","uncertain"}
    assert SEMANTIC_QUALITY_OUTPUT_TOKENS<1800


class SemanticAPIProvider(MockModelProvider):
    def __init__(self,response,result):super().__init__(response);self.semantic_result=result;self.semantic_calls=0
    def generate_semantic_quality(self,*,candidates,timeout_seconds):
        self.semantic_calls+=1
        return {"results":[{"field_id":item["field_id"],"item_index":item["item_index"],"result":self.semantic_result,"reason":"truncated_phrase" if self.semantic_result=="incomplete" else "context_insufficient"} for item in candidates]},{"latency_ms":1,"input_tokens":10,"output_tokens":5,"total_tokens":15}


def test_required_semantic_failure_returns_normalized_safe_partial(monkeypatch):
    client,_,_,engine=_client(monkeypatch);raw=_model_response();raw["rationale"]="PRIVATE SEMANTIC RATIONALE—";provider=SemanticAPIProvider(raw,"incomplete")
    monkeypatch.setattr(routes.decision_analysis_orchestrator,"provider",provider)
    try:
        response=client.post("/personal/ask",headers={"Authorization":"Bearer test"},json={"message":"I have two job offers. Offer A is remote. Offer B has a commute. Which should I choose?"})
        assert response.status_code==200 and response.json()["mode"]=="ANALYSIS_PARTIAL"
        assert provider.calls==1 and provider.semantic_calls==1 and "PRIVATE SEMANTIC RATIONALE" not in response.text
    finally:engine.dispose()


def test_semantic_classifier_preserves_tenant_isolation_and_two_call_max(monkeypatch):
    client,_,active,engine=_client(monkeypatch);raw=_model_response();raw["rationale"]="A bounded canonical rationale—";provider=SemanticAPIProvider(raw,"complete")
    monkeypatch.setattr(routes.decision_analysis_orchestrator,"provider",provider)
    try:
        response=client.post("/personal/ask",headers={"Authorization":"Bearer test"},json={"message":"I have two job offers. Offer A is remote. Offer B has a commute. Which should I choose?"})
        assert response.status_code==200 and response.json()["telemetry"]["provider_calls"]==2
        session_id=response.json()["session_id"];active["identity"]=_identity(user_id=2,organization_id=2,workspace_id=2)
        assert client.post("/personal/ask",headers={"Authorization":"Bearer test"},json={"session_id":session_id,"message":"Continue"}).status_code==404
        assert provider.calls==1 and provider.semantic_calls==1
    finally:engine.dispose()
