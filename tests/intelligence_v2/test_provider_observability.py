import logging

from app.intelligence_v2.model_provider import InvalidModelResponseError, ProviderTimeoutError, ProviderUnavailableError
from app.intelligence_v2.orchestrator import DecisionAnalysisOrchestrator
from tests.intelligence_v2.test_analysis_orchestrator import ready_personal_state, response
from tests.intelligence_v2.test_decision_v2 import session


class SequenceProvider:
    provider_name="mock"; model_name="observability-test"; capabilities={"structured_output"}
    def __init__(self,*items): self.items=list(items); self.calls=0
    def generate_structured(self,**_):
        self.calls+=1; item=self.items.pop(0)
        if isinstance(item,Exception): raise item
        return item,{"provider":"mock","model":"observability-test","input_tokens":11,"reasoning_tokens":2,"output_tokens":7,"total_tokens":18,"latency_ms":3,"provider_protocol_state":"completed","finish_reason":"completed","content_present":True}


def messages(caplog): return [record.message for record in caplog.records if "provider_attempt=" in record.message]


def analyze(session,caplog,*items):
    caplog.set_level(logging.WARNING,logger="uvicorn.error")
    return DecisionAnalysisOrchestrator(SequenceProvider(*items)).analyze(ready_personal_state(session))


def test_initial_success_emits_ordered_safe_stages_and_metrics(session,caplog):
    execution=analyze(session,caplog,response())
    logs=messages(caplog)
    assert execution.status=="READY"
    assert [line.split("provider_stage=",1)[1].split()[0] for line in logs]==["request_started","response_received","parse_started","grounding_started"]
    assert "provider_attempt=initial" in " ".join(logs)
    assert "input_tokens=11" in logs[1] and "content_present=yes" in logs[1]


def test_initial_timeout_then_retry_success_preserves_initial_failure(session,caplog):
    execution=analyze(session,caplog,ProviderTimeoutError("private timeout","timeout",{"latency_ms":90}),response())
    logs="\n".join(messages(caplog))
    assert execution.status=="READY" and execution.usage["initial_error_category"]=="timeout"
    assert "provider_attempt=initial provider_stage=request_failed error_category=timeout latency_ms=90" in logs
    assert "provider_attempt=retry provider_stage=response_received" in logs


def test_initial_incomplete_then_retry_success_preserves_reason(session,caplog):
    error=InvalidModelResponseError("private output","incomplete_max_tokens",{"provider_protocol_state":"incomplete","incomplete_reason":"max_output_tokens","content_present":True})
    execution=analyze(session,caplog,error,response())
    logs="\n".join(messages(caplog))
    assert execution.status=="READY" and execution.usage["initial_error_category"]=="incomplete_max_tokens"
    assert "provider_response_state=incomplete" in logs and "incomplete_reason=max_output_tokens" in logs and "content_present=yes" in logs


def test_initial_timeout_retry_timeout_records_both_failures(session,caplog):
    execution=analyze(session,caplog,ProviderTimeoutError("first private","timeout"),ProviderTimeoutError("second private","timeout"))
    assert execution.status=="PARTIAL"
    assert execution.usage["initial_error_category"]==execution.usage["retry_error_category"]=="timeout"
    assert sum("provider_stage=request_failed" in line for line in messages(caplog))==2


def test_incomplete_then_invalid_response_records_independent_categories(session,caplog):
    execution=analyze(session,caplog,InvalidModelResponseError("private","incomplete_max_tokens"),InvalidModelResponseError("private body","invalid_json"))
    logs="\n".join(messages(caplog))
    assert execution.status=="PARTIAL"
    assert execution.usage["initial_error_category"]=="incomplete_max_tokens"
    assert execution.usage["retry_error_category"]=="invalid_model_response"
    assert "private" not in logs and "invalid_model_response" in logs


def test_rate_limit_then_retry_failure_is_distinct(session,caplog):
    execution=analyze(session,caplog,ProviderUnavailableError("private","rate_limit",{"http_status":429}),ProviderTimeoutError("private","timeout"))
    logs="\n".join(messages(caplog))
    assert execution.status=="PARTIAL" and execution.usage["initial_error_category"]=="rate_limit" and execution.usage["retry_error_category"]=="timeout"
    assert "error_category=rate_limit http_status=429" in logs


def test_provider_unavailable_then_retry_failure_is_distinct(session,caplog):
    execution=analyze(session,caplog,ProviderUnavailableError("private","provider_unavailable"),InvalidModelResponseError("private","empty_content",{"content_present":False}))
    logs="\n".join(messages(caplog))
    assert execution.status=="PARTIAL" and execution.usage["initial_error_category"]=="provider_unavailable" and execution.usage["retry_error_category"]=="empty_content"
    assert "content_present=no" in logs


def test_malformed_structured_result_logs_parse_failure_without_content(session,caplog):
    malformed={"problem_summary":"private provider response"}
    execution=analyze(session,caplog,malformed)
    logs="\n".join(messages(caplog))
    assert execution.status=="ANALYSIS_FAILED" and "provider_stage=parse_failed error_category=invalid_model_response" in logs
    assert "private provider response" not in logs


def test_grounding_failure_occurs_after_response_and_does_not_log_fact(session,caplog):
    raw=response("invented-private-id"); raw["rationale"]="Private factual response with 999 unsupported units."
    execution=analyze(session,caplog,raw)
    logs=messages(caplog); stages=[line.split("provider_stage=",1)[1].split()[0] for line in logs]
    assert execution.status=="ANALYSIS_FAILED"
    assert stages.index("response_received") < stages.index("grounding_started") < stages.index("grounding_failed")
    assert "invented-private-id" not in "\n".join(logs) and "999" not in "\n".join(logs)
