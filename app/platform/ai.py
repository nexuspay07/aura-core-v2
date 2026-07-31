"""Provider-neutral AI orchestration contracts; providers never leak into pipelines."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any


@dataclass(frozen=True)
class AIRequest:
    prompt: str
    system_prompt: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AIResponse:
    content: str
    provider: str
    latency_ms: int
    usage: dict[str, int] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


class AIProvider(ABC):
    key: str

    @abstractmethod
    def generate(self, request: AIRequest) -> AIResponse: ...


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, AIProvider] = {}
        self._failures: dict[str, int] = {}

    def register(self, provider: AIProvider) -> None:
        if not provider.key or provider.key in self._providers:
            raise ValueError(f"Invalid or duplicate provider '{provider.key}'.")
        self._providers[provider.key] = provider
        self._failures[provider.key] = 0

    def get(self, key: str) -> AIProvider:
        if key not in self._providers:
            raise ValueError(f"AI provider '{key}' is not installed.")
        return self._providers[key]

    def healthy(self, key: str) -> bool:
        return self._failures.get(key, 0) < 3

    def keys(self) -> list[str]:
        return sorted(self._providers)

    def record_failure(self, key: str) -> None: self._failures[key] = self._failures.get(key, 0) + 1
    def record_success(self, key: str) -> None: self._failures[key] = 0


class AIOrchestrator:
    def __init__(self, registry: ProviderRegistry) -> None: self.registry = registry

    def generate(self, request: AIRequest, *, providers: list[str]) -> AIResponse:
        errors = []
        for key in providers:
            if not self.registry.healthy(key):
                errors.append(f"{key}: circuit open")
                continue
            try:
                started = perf_counter()
                response = self.registry.get(key).generate(request)
                self.registry.record_success(key)
                return AIResponse(content=response.content, provider=response.provider, latency_ms=round((perf_counter() - started) * 1000), usage=response.usage, metadata=response.metadata)
            except Exception as error:
                self.registry.record_failure(key)
                errors.append(f"{key}: {type(error).__name__}")
        raise RuntimeError(f"No AI provider completed the request ({'; '.join(errors)}).")


class DeterministicProvider(AIProvider):
    """Installed local provider used when no external provider is configured."""
    key = "deterministic"

    def generate(self, request: AIRequest) -> AIResponse:
        return AIResponse(content=f"Aura provider orchestration received: {request.prompt}", provider=self.key, latency_ms=0, metadata={"deterministic": True})
