from __future__ import annotations
from datetime import datetime, timezone
import os
import time
from urllib.parse import urlparse

import httpx

from app.current_intelligence.contracts import CurrentQuery, CurrentResult, CurrentSource


class CurrentProviderError(RuntimeError):
    def __init__(self, category: str): super().__init__(category); self.category = category


class UnconfiguredCurrentProvider:
    provider_name = "unconfigured"
    def search(self, query: CurrentQuery) -> CurrentResult: raise CurrentProviderError("unconfigured")


class TavilyCurrentProvider:
    provider_name = "tavily"
    endpoint = "https://api.tavily.com/search"

    def __init__(self, *, api_key: str | None = None, timeout: float | None = None, search_depth: str | None = None):
        self._api_key = api_key or os.getenv("TAVILY_API_KEY")
        if not self._api_key: raise CurrentProviderError("unconfigured")
        self.timeout = timeout or _float_env("AURA_CURRENT_TIMEOUT_SECONDS", 12, 1, 30)
        depth = (search_depth or os.getenv("AURA_CURRENT_SEARCH_DEPTH", "basic")).lower()
        self.search_depth = depth if depth in {"basic", "advanced"} else "basic"

    def search(self, query: CurrentQuery) -> CurrentResult:
        started = time.monotonic()
        try:
            response = httpx.post(self.endpoint, json={"api_key": self._api_key, "query": query.text, "search_depth": self.search_depth, "max_results": query.max_results, "include_answer": False, "include_raw_content": False}, timeout=self.timeout)
            response.raise_for_status(); body = response.json()
        except httpx.TimeoutException as error: raise CurrentProviderError("timeout") from error
        except httpx.HTTPStatusError as error:
            category = "rate_limit" if error.response.status_code == 429 else "authentication" if error.response.status_code in {401, 403} else "unavailable"
            raise CurrentProviderError(category) from error
        except Exception as error: raise CurrentProviderError("unavailable") from error
        now = datetime.now(timezone.utc); sources = []
        for index, item in enumerate(body.get("results", []) if isinstance(body, dict) else []):
            if not isinstance(item, dict): continue
            title, url, content = item.get("title"), item.get("url"), item.get("content")
            parsed = urlparse(url) if isinstance(url, str) else None
            if not (isinstance(title, str) and parsed and parsed.scheme == "https" and parsed.netloc and isinstance(content, str) and content.strip()): continue
            published = _published(item.get("published_at") or item.get("published_date"))
            sources.append(CurrentSource(title=title[:300], url=url, domain=parsed.netloc.lower().removeprefix("www."), retrieved_at=now, content=content[:4000], published_at=published, relevance_score=item.get("score") if isinstance(item.get("score"), (int, float)) else None, provider_id=str(index)))
        usage = {"provider": self.provider_name, "latency_ms": round((time.monotonic()-started)*1000), "result_count": len(sources)}
        if isinstance(body, dict) and isinstance(body.get("response_time"), (int, float)): usage["provider_response_time"] = body["response_time"]
        return CurrentResult(str(body.get("query") or query.text), sources, usage)


def _float_env(name, default, low, high):
    try: value = float(os.getenv(name, str(default)))
    except ValueError: value = default
    return min(max(value, low), high)


def _published(value):
    if not isinstance(value, str): return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)
    except ValueError: return None


def configured_current_provider():
    if os.getenv("AURA_CURRENT_PROVIDER", "").lower() == "tavily":
        try: return TavilyCurrentProvider()
        except CurrentProviderError: pass
    return UnconfiguredCurrentProvider()
