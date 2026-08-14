"""Provider-neutral embeddings for the V2 retrieval seam.

The deterministic implementation is intentionally lexical-hash based.  It is
useful for tests and offline deployments, but is never represented as a real
semantic model.  A future local or hosted provider only needs this protocol.
"""

from __future__ import annotations

from hashlib import sha256
from math import sqrt
import os
import re
from typing import Protocol


class EmbeddingProvider(Protocol):
    provider_name: str
    dimension: int

    def embed(self, text: str) -> list[float]: ...

    def embed_many(self, texts: list[str]) -> list[list[float]]: ...


class DeterministicEmbeddingProvider:
    """Small stable token-hash embedding used only as a retrieval signal."""

    provider_name = "deterministic-token-hash-v1"
    dimension = 64

    def embed(self, text: str) -> list[float]:
        values = [0.0] * self.dimension
        for token in re.findall(r"[a-z0-9]+(?:\.[0-9]+)?", text.lower()):
            bucket = int.from_bytes(sha256(token.encode("utf-8")).digest()[:4], "big") % self.dimension
            values[bucket] += 1.0
        norm = sqrt(sum(value * value for value in values))
        return [value / norm for value in values] if norm else values

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(text) for text in texts]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    return sum(a * b for a, b in zip(left, right))


deterministic_embedding_provider = DeterministicEmbeddingProvider()


def configured_embedding_provider() -> EmbeddingProvider:
    """Select an approved provider seam without making boot depend on credentials.

    No real provider ships in this stage.  Unknown/unconfigured provider names
    safely use the deterministic hybrid fallback; callers can expose that
    degraded semantic status without leaking configuration secrets.
    """
    provider = os.getenv("AURA_EMBEDDING_PROVIDER", "deterministic").lower()
    _model = os.getenv("AURA_EMBEDDING_MODEL")  # Reserved for a later provider adapter.
    if provider in {"", "deterministic", "local-fallback"}:
        return deterministic_embedding_provider
    return deterministic_embedding_provider
