"""Structured request telemetry contract with no vendor dependency."""

from dataclasses import dataclass, field
from time import perf_counter
from uuid import uuid4


@dataclass
class ExecutionMetrics:
    request_id: str = field(default_factory=lambda: str(uuid4()))
    organization_id: int | None = None
    workspace_id: int | None = None
    domain: str | None = None
    industry: str | None = None
    provider: str | None = None
    pipeline_stages: list[dict] = field(default_factory=list)

    def stage(self, name: str):
        started = perf_counter()
        def complete(**attributes):
            self.pipeline_stages.append({"name": name, "duration_ms": round((perf_counter() - started) * 1000), **attributes})
        return complete
