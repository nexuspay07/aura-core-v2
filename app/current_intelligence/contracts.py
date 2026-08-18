from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol


@dataclass(frozen=True)
class CurrentQuery:
    text: str
    max_results: int = 6


@dataclass(frozen=True)
class CurrentSource:
    title: str
    url: str
    domain: str
    retrieved_at: datetime
    content: str
    published_at: datetime | None = None
    relevance_score: float | None = None
    source_type: str = "web"
    provider_id: str | None = None


@dataclass(frozen=True)
class CurrentResult:
    query: str
    sources: list[CurrentSource]
    usage: dict[str, Any] = field(default_factory=dict)


class CurrentRetrievalProvider(Protocol):
    provider_name: str
    def search(self, query: CurrentQuery) -> CurrentResult: ...
