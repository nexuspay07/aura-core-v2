"""Provider-neutral, bounded model-generation seam for Intelligence V2."""
from __future__ import annotations
import json, os, time
from enum import Enum
from typing import Any, Protocol

class ModelProviderError(RuntimeError):
    def __init__(self, message: str, category: str = "provider_or_sdk_error", diagnostics: dict | None = None):
        super().__init__(message); self.category = category; self.diagnostics = diagnostics or {}
class ProviderUnavailableError(ModelProviderError): pass
class ProviderTimeoutError(ModelProviderError): pass
class InvalidModelResponseError(ModelProviderError): pass

class ProviderResponseState(str, Enum):
    COMPLETED_STRUCTURED="COMPLETED_STRUCTURED"; REFUSAL="REFUSAL"; INCOMPLETE_MAX_TOKENS="INCOMPLETE_MAX_TOKENS"; EMPTY_CONTENT="EMPTY_CONTENT"; INVALID_JSON="INVALID_JSON"; SCHEMA_MISMATCH="SCHEMA_MISMATCH"; PROVIDER_ERROR="PROVIDER_ERROR"

def _bounded_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try: value = int(os.getenv(name, str(default)))
    except ValueError: return default
    return min(max(value, minimum), maximum)

def analysis_timeout_seconds() -> int:
    return _bounded_int("AURA_AI_TIMEOUT_SECONDS", 90, 10, 300)

def analysis_max_output_tokens() -> int:
    return _bounded_int("AURA_AI_MAX_OUTPUT_TOKENS", 1800, 256, 1800)

def analysis_reasoning_effort() -> str:
    value=os.getenv("AURA_AI_REASONING_EFFORT", "medium").lower()
    return value if value in {"none","low","medium","high"} else "medium"

def explicit_reasoning_effort() -> str | None:
    value=os.getenv("AURA_AI_REASONING_EFFORT")
    return value.lower() if value and value.lower() in {"none","low","medium","high"} else None

def analysis_verbosity() -> str:
    value=os.getenv("AURA_AI_VERBOSITY", "low").lower()
    return value if value in {"low", "medium", "high"} else "low"

def model_analysis_schema() -> dict[str, Any]:
    string=lambda maximum: {"type":"string","maxLength":maximum}
    strings=lambda count,length=180: {"type":"array","items":string(length),"maxItems":count}
    alternative={"type":"object","additionalProperties":False,"properties":{"option":string(160),"benefits":strings(2),"downsides":strings(2),"evidence_ids":strings(4,80),"conditions_for_success":strings(2)},"required":["option","benefits","downsides","evidence_ids","conditions_for_success"]}
    properties={"problem_summary":string(280),"alternatives":{"type":"array","items":alternative,"minItems":1,"maxItems":3},"recommended_option":string(200),"rationale":string(600),"risks":strings(4),"assumptions_used":strings(3),"unresolved_questions":strings(4),"recommendation_change_conditions":strings(4)}
    return {"type":"object","additionalProperties":False,"properties":properties,"required":list(properties)}

# Compatibility alias for callers that previously imported this helper.
def analysis_result_schema() -> dict[str, Any]:
    return model_analysis_schema()

class ModelProvider(Protocol):
    provider_name: str
    model_name: str
    capabilities: set[str]
    def generate_structured(self, *, system: str, payload: dict[str, Any], timeout_seconds: float) -> tuple[dict[str, Any],dict[str,Any]]: ...
    def health_check(self) -> bool: ...

class UnconfiguredModelProvider:
    provider_name="unconfigured"; model_name="none"; capabilities=set()
    def generate_structured(self, **_): raise ProviderUnavailableError("No V2 model provider is configured")
    def health_check(self): return False

class OpenAIModelProvider:
    provider_name="openai"; capabilities={"structured_output"}
    def __init__(self, model_name: str | None=None, api_key: str | None=None, max_output_tokens: int | None=None, reasoning_effort: str | None=None):
        self.model_name=model_name or os.getenv("AURA_AI_MODEL", "gpt-4o-mini"); self._api_key=api_key or os.getenv("OPENAI_API_KEY")
        self.max_output_tokens=max_output_tokens or analysis_max_output_tokens()
        self.reasoning_effort=reasoning_effort or analysis_reasoning_effort()
        if not self._api_key: raise ProviderUnavailableError("OpenAI provider is not configured")
    def generate_structured(self, *, system, payload, timeout_seconds, reasoning_effort=None):
        try:
            from openai import OpenAI
            started=time.monotonic(); client=OpenAI(api_key=self._api_key,timeout=timeout_seconds,max_retries=0)
            response=client.responses.create(**self.request_kwargs(system=system,payload=payload,reasoning_effort=reasoning_effort))
            return self._parse_response(response, started)
        except TimeoutError as error: raise ProviderTimeoutError("Provider timed out", "timeout", self._exception_diagnostics(error, "timeout")) from error
        except json.JSONDecodeError as error: raise InvalidModelResponseError("Provider returned invalid structured output", "structured_output_error") from error
        except ModelProviderError: raise
        except Exception as error:
            raise self._map_request_exception(error) from error
    def health_check(self): return bool(self._api_key)
    def request_kwargs(self, *, system, payload, reasoning_effort=None):
        request={"model":self.model_name,"instructions":system,"input":json.dumps(payload,separators=(",",":")),"text":{"format":{"type":"json_schema","name":"model_analysis_result","strict":True,"schema":model_analysis_schema()},"verbosity":analysis_verbosity()},"max_output_tokens":self.max_output_tokens,"store":False}
        if self.model_name.lower().startswith("gpt-5"): request["reasoning"]={"effort":reasoning_effort or self.reasoning_effort}
        return request
    def _exception_diagnostics(self, error, category):
        """Never retain arbitrary provider bodies because they can echo request data."""
        safe = {
            "provider": "openai", "model": self.model_name,
            "exception_type": type(error).__name__, "response_state": "request_error",
            "error_category": category,
        }
        for source, target in (("status_code", "http_status"), ("code", "error_code"), ("type", "error_type")):
            value = getattr(error, source, None)
            if isinstance(value, (str, int, float, bool)):
                safe[target] = value
        return safe
    def _map_request_exception(self, error):
        try:
            from openai import APIConnectionError, APIError, APITimeoutError, AuthenticationError, BadRequestError, NotFoundError, PermissionDeniedError, RateLimitError
        except ImportError:  # pragma: no cover - provider package is an optional dependency
            APIConnectionError=APIError=APITimeoutError=AuthenticationError=BadRequestError=NotFoundError=PermissionDeniedError=RateLimitError=()  # type: ignore[assignment]
        mappings=(
            (AuthenticationError,"authentication_error","OpenAI authentication failed."),
            (PermissionDeniedError,"permission_error","OpenAI permission was denied."),
            (RateLimitError,"rate_limit","OpenAI rate limit reached."),
            (NotFoundError,"model_not_found","Configured OpenAI model was not found."),
            (BadRequestError,"bad_request","OpenAI rejected the Responses request."),
            (APITimeoutError,"timeout","OpenAI request timed out."),
            (APIConnectionError,"api_connection_error","OpenAI connection failed."),
            (TypeError,"responses_configuration_error","Responses request configuration is invalid."),
            (ValueError,"responses_configuration_error","Responses request configuration is invalid."),
            (APIError,"provider_unavailable","OpenAI provider request failed."),
        )
        for exception_type,category,message in mappings:
            if isinstance(error,exception_type):
                cls=ProviderTimeoutError if category=="timeout" else ProviderUnavailableError
                return cls(message,category,self._exception_diagnostics(error,category))
        return ProviderUnavailableError("OpenAI provider request failed.","unknown_provider_error",self._exception_diagnostics(error,"unknown_provider_error"))
    def _parse_response(self, response, started):
        status=getattr(response,"status",None); incomplete=getattr(response,"incomplete_details",None); error=getattr(response,"error",None)
        output=getattr(response,"output",None) or []
        content_parts=[part for item in output for part in (getattr(item,"content",None) or [])]
        refusal=next((getattr(part,"refusal",None) for part in content_parts if getattr(part,"refusal",None)),None)
        content=getattr(response,"output_text",None) or next((getattr(part,"text",None) for part in content_parts if getattr(part,"type",None)=="output_text" and getattr(part,"text",None)),None)
        usage=getattr(response,"usage",None)
        completion=getattr(usage,"output_tokens",None); details=getattr(usage,"output_tokens_details",None); reasoning=getattr(details,"reasoning_tokens",None)
        reason=getattr(incomplete,"reason",None) if incomplete else None
        diagnostics={"provider":"openai","model":self.model_name,"request_id":getattr(response,"_request_id",None) or getattr(response,"id",None),"finish_reason":status,"provider_protocol_state":status,"incomplete_reason":reason,"response_error_type":type(error).__name__ if error else None,"refusal_present":bool(refusal),"content_present":bool(content),"content_length":len(content) if isinstance(content,str) else 0,"input_tokens":getattr(usage,"input_tokens",None),"completion_tokens":completion,"reasoning_tokens":reasoning,"visible_output_tokens":completion-reasoning if isinstance(completion,int) and isinstance(reasoning,int) else completion,"total_tokens":getattr(usage,"total_tokens",None),"output_tokens":completion,"latency_ms":round((time.monotonic()-started)*1000)}
        if refusal: raise InvalidModelResponseError("Provider refusal", "refusal", diagnostics)
        if status=="incomplete": raise InvalidModelResponseError("Provider output was truncated" if reason=="max_output_tokens" else "Provider response incomplete", "incomplete_max_tokens" if reason=="max_output_tokens" else "provider_error", diagnostics)
        if status=="failed": raise InvalidModelResponseError("Provider response failed", "provider_error", diagnostics)
        if status!="completed": raise InvalidModelResponseError("Unexpected provider response state", "provider_error", diagnostics)
        if not isinstance(content,str) or not content.strip(): raise InvalidModelResponseError("Provider returned empty content", "empty_content", diagnostics)
        try: data=json.loads(content)
        except json.JSONDecodeError as error: raise InvalidModelResponseError("Provider returned invalid JSON", "invalid_json", diagnostics) from error
        diagnostics["structured_parse_status"]=ProviderResponseState.COMPLETED_STRUCTURED.value
        return data,diagnostics

class MockModelProvider:
    provider_name="mock"; model_name="deterministic-test"; capabilities={"structured_output"}
    def __init__(self,response:dict[str,Any] | Exception): self.response=response;self.calls=0
    def generate_structured(self, **_):
        self.calls+=1
        if isinstance(self.response,Exception): raise self.response
        return self.response,{"provider":self.provider_name,"model":self.model_name,"input_tokens":1,"output_tokens":1,"latency_ms":0}
    def health_check(self): return True

def configured_model_provider() -> ModelProvider:
    if os.getenv("AURA_AI_PROVIDER", "").lower()=="openai":
        try: return OpenAIModelProvider()
        except ProviderUnavailableError: return UnconfiguredModelProvider()
    return UnconfiguredModelProvider()
