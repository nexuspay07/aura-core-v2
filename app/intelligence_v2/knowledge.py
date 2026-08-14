"""Adapter from the existing persisted knowledge facts into V2 evidence."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import or_, select

from app.db.knowledge_table import knowledge_table
from app.intelligence_v2.contracts import EvidenceItem, EvidenceSourceType
from app.intelligence_v2.retrieval import _tokens, _utc


class KnowledgeEvidenceAdapter:
    candidate_limit = 100
    returned_limit = 12

    def retrieve(self, *, db, organization_id: int, workspace_id: int, user_id: int, query: str, limit: int | None = None) -> list[EvidenceItem]:
        rows = db.execute(
            select(knowledge_table)
            .where(knowledge_table.c.organization_id == organization_id, or_(knowledge_table.c.workspace_id.is_(None), knowledge_table.c.workspace_id == workspace_id))
            .order_by(knowledge_table.c.created_at.desc(), knowledge_table.c.id.desc())
            .limit(self.candidate_limit)
        ).mappings().all()
        query_tokens = _tokens(query)
        ranked = []
        for row in rows:
            if row.get("user_id") is not None and row["user_id"] != user_id:
                continue
            content = f"{row['fact_type']}: {row['fact_value']}"
            tokens = _tokens(content)
            overlap = len(query_tokens & tokens) / max(1, len(query_tokens | tokens))
            # Known facts are intentionally returned even where broad wording has no lexical match.
            score = overlap + (0.1 if row["fact_type"].lower().replace("_", " ") in query.lower() else 0.0)
            created = _utc(row.get("created_at"))
            item = EvidenceItem(
                id=f"knowledge:{row['id']}", source_type=EvidenceSourceType.KNOWLEDGE_DOCUMENT, source_name="knowledge",
                content=content, structured_value={"fact_type": row["fact_type"], "fact_value": row["fact_value"]},
                organization_id=organization_id, workspace_id=row.get("workspace_id"), timestamp=created,
                reliability="persisted_knowledge", permission_scope="user-private" if row.get("user_id") else ("workspace" if row.get("workspace_id") else "organization"),
                citation_label=f"Knowledge fact #{row['id']}", provenance={"table": "knowledge", "record_id": row["id"], "source": row.get("source"), "score": round(score, 6), "why_matched": ["fact type/value lexical relevance"]},
            )
            ranked.append((score, row["id"], item))
        ranked.sort(key=lambda entry: (-entry[0], -entry[1]))
        return [entry[2] for entry in ranked[:limit or self.returned_limit]]


knowledge_evidence_adapter = KnowledgeEvidenceAdapter()
