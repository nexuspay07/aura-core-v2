"""Provider-neutral language capability seam for Unified Aura."""
from __future__ import annotations

import os
import time
from typing import Protocol

from app.intelligence_v2.model_provider import ProviderTimeoutError, ProviderUnavailableError, analysis_timeout_seconds, analysis_verbosity
from app.unified_intelligence.contracts import ModelRequest, ModelResult


class LanguageModelProvider(Protocol):
    provider_name: str
    model_name: str
    capabilities: set[str]
    def generate(self, request: ModelRequest) -> ModelResult: ...


class UnconfiguredLanguageModelProvider:
    provider_name = "unconfigured"
    model_name = "none"
    capabilities: set[str] = set()
    def generate(self, request: ModelRequest) -> ModelResult:
        raise ProviderUnavailableError("No general language model provider is configured")


class OpenAILanguageModelProvider:
    provider_name = "openai"
    capabilities = {"natural_text_generation", "summarization"}

    def __init__(self, *, api_key: str | None = None, model_name: str | None = None):
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model_name = model_name or os.getenv("AURA_GENERAL_MODEL", os.getenv("AURA_AI_MODEL", "gpt-4o-mini"))
        if not self._api_key:
            raise ProviderUnavailableError("OpenAI provider is not configured")

    @staticmethod
    def max_output_tokens() -> int:
        try: value = int(os.getenv("AURA_GENERAL_MAX_OUTPUT_TOKENS", "1600"))
        except ValueError: value = 1600
        return min(max(value, 256), 3000)

    @staticmethod
    def reasoning_effort() -> str:
        value = os.getenv("AURA_GENERAL_REASONING_EFFORT", "low").lower()
        return value if value in {"none", "low", "medium", "high"} else "low"

    def request_kwargs(self, request: ModelRequest) -> dict:
        kwargs = {
            "model": self.model_name, "instructions": request.system, "input": request.prompt,
            "text": {"verbosity": analysis_verbosity()},
            "max_output_tokens": self.max_output_tokens(), "store": False,
        }
        if self.model_name.lower().startswith("gpt-5"):
            kwargs["reasoning"] = {"effort": self.reasoning_effort()}
        return kwargs

    def generate(self, request: ModelRequest) -> ModelResult:
        try:
            from openai import OpenAI
            started = time.monotonic()
            response = OpenAI(api_key=self._api_key, timeout=analysis_timeout_seconds(), max_retries=0).responses.create(**self.request_kwargs(request))
            content = getattr(response, "output_text", None)
            if not isinstance(content, str) or not content.strip():
                raise ProviderUnavailableError("Provider returned no usable content")
            usage = getattr(response, "usage", None)
            output = getattr(usage, "output_tokens", None)
            details = getattr(usage, "output_tokens_details", None)
            reasoning = getattr(details, "reasoning_tokens", None)
            return ModelResult(content.strip(), {
                "provider": self.provider_name, "model": self.model_name,
                "input_tokens": getattr(usage, "input_tokens", None), "output_tokens": output,
                "reasoning_tokens": reasoning, "total_tokens": getattr(usage, "total_tokens", None),
                "latency_ms": round((time.monotonic() - started) * 1000),
            })
        except ProviderUnavailableError:
            raise
        except TimeoutError as error:
            raise ProviderTimeoutError("General model timed out", "timeout") from error
        except Exception as error:
            try:
                from openai import APITimeoutError, AuthenticationError, PermissionDeniedError, RateLimitError
            except ImportError:  # pragma: no cover
                APITimeoutError=AuthenticationError=PermissionDeniedError=RateLimitError=()  # type: ignore[assignment]
            if isinstance(error, APITimeoutError):
                raise ProviderTimeoutError("General model timed out", "timeout", {"provider":self.provider_name,"model":self.model_name,"exception_type":type(error).__name__}) from error
            category = "authentication_error" if isinstance(error, AuthenticationError) else "permission_error" if isinstance(error, PermissionDeniedError) else "rate_limit" if isinstance(error, RateLimitError) else "provider_unavailable"
            # Provider bodies are intentionally not retained or returned.
            raise ProviderUnavailableError("General model provider request failed", category, {
                "provider": self.provider_name, "model": self.model_name,
                "exception_type": type(error).__name__, "error_category": category,
            }) from error


def configured_language_model_provider() -> LanguageModelProvider:
    if os.getenv("AURA_GENERAL_PROVIDER", os.getenv("AURA_AI_PROVIDER", "")).lower() == "openai":
        try:
            return OpenAILanguageModelProvider()
        except ProviderUnavailableError:
            pass
    return UnconfiguredLanguageModelProvider()


class ModelRouter:
    def __init__(self, provider: LanguageModelProvider | None = None):
        self.provider = provider or configured_language_model_provider()

    def generate(self, request: ModelRequest) -> ModelResult:
        if request.capability not in self.provider.capabilities:
            raise ProviderUnavailableError("Configured provider lacks the requested model capability")
        return self.provider.generate(request)


model_router = ModelRouter()
