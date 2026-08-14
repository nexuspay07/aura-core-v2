"""Bounded, deterministic and tenant-safe V2 evidence retrieval."""

from __future__ import annotations

from datetime import datetime, timezone
import re

from sqlalchemy import or_, select

from app.db.memory_table import memory_table
from app.intelligence_v2.contracts import EvidenceItem, EvidenceSourceType
from app.intelligence_v2.embeddings import EmbeddingProvider, cosine_similarity, deterministic_embedding_provider


def _tokens(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+(?:\.[0-9]+)?", value.lower()))


def _utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class MemoryEvidenceRetriever:
    """Retrieves at most ``candidate_limit`` rows and returns bounded evidence.

    Scope: organization-global rows have null workspace/user; workspace rows
    match the active workspace; user-private rows match the requesting user.
    Session filtering is honoured only when a persisted metadata.session_id is
    present.  The current memory schema has no first-class session column.
    """

    candidate_limit = 100
    returned_limit = 12

    def __init__(self, embedding_provider: EmbeddingProvider = deterministic_embedding_provider):
        self.embedding_provider = embedding_provider

    def retrieve(self, *, db, organization_id: int, workspace_id: int, user_id: int, query: str, session_id: int | None = None, limit: int | None = None) -> list[EvidenceItem]:
        scope = [memory_table.c.workspace_id.is_(None), memory_table.c.workspace_id == workspace_id]
        rows = db.execute(
            select(memory_table)
            .where(memory_table.c.organization_id == organization_id, or_(*scope))
            .order_by(memory_table.c.created_at.desc(), memory_table.c.id.desc())
            .limit(self.candidate_limit)
        ).mappings().all()
        query_tokens = _tokens(query)
        query_vector = self.embedding_provider.embed(query)
        ranked: list[tuple[float, int, EvidenceItem]] = []
        now = datetime.now(timezone.utc)
        for row in rows:
            metadata = row.get("metadata") or {}
            # A user-owned memory is private; no user id is organization/workspace-visible.
            if row.get("user_id") is not None and row["user_id"] != user_id:
                continue
            stored_session = metadata.get("session_id")
            if stored_session is not None and stored_session != session_id:
                continue
            content = row["content"]
            content_tokens = _tokens(content)
            lexical = len(query_tokens & content_tokens) / max(1, len(query_tokens | content_tokens))
            exact = 0.18 if any(token in content_tokens for token in query_tokens if any(char.isdigit() for char in token)) else 0.0
            semantic = cosine_similarity(query_vector, self.embedding_provider.embed(content))
            created = _utc(row.get("created_at"))
            age_days = max(0.0, (now - created).total_seconds() / 86400) if created else 365.0
            recency = 1.0 / (1.0 + age_days / 30.0)
            workspace_bonus = 0.08 if row.get("workspace_id") == workspace_id else 0.03
            score = (0.55 * lexical) + (0.20 * semantic) + (0.12 * recency) + workspace_bonus + exact
            why = ["lexical overlap" if lexical else "contextual token similarity", f"{self.embedding_provider.provider_name} similarity", "recency", "workspace scope" if row.get("workspace_id") else "organization scope"]
            scope_name = "user-private" if row.get("user_id") else ("workspace" if row.get("workspace_id") else "organization")
            item = EvidenceItem(
                id=f"memory:{row['id']}", source_type=EvidenceSourceType.MEMORY, source_name="memory",
                content=content, organization_id=organization_id, workspace_id=row.get("workspace_id"),
                timestamp=created, freshness=f"{age_days:.0f} days old" if created else None,
                reliability="user_statement" if row.get("memory_type") == "conversation" else "persisted_memory",
                permission_scope=scope_name, citation_label=f"Memory #{row['id']}",
                provenance={"table": "memory", "record_id": row["id"], "score": round(score, 6), "why_matched": why, "metadata": metadata},
            )
            ranked.append((score, row["id"], item))
        ranked.sort(key=lambda entry: (-entry[0], -entry[1]))
        return [entry[2] for entry in ranked[:limit or self.returned_limit]]


memory_evidence_retriever = MemoryEvidenceRetriever()
