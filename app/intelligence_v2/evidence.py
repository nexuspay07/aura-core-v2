"""Evidence normalization that preserves provenance and exposes ambiguity."""

from __future__ import annotations

import re

from app.intelligence_v2.contracts import EvidenceConflict, EvidenceItem


def deduplicate_evidence(items: list[EvidenceItem]) -> list[EvidenceItem]:
    """Remove exact duplicate claims only; provenance remains on the retained fact."""
    seen: set[tuple[str, str]] = set()
    result = []
    for item in items:
        normalized = (item.content or str(item.structured_value or "")).lower().replace("_", " ")
        normalized = re.sub(r"\s*(?:is|:)\s*", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        key = (item.organization_id and str(item.organization_id) or "", normalized)
        if normalized and key in seen:
            continue
        if normalized:
            seen.add(key)
        result.append(item)
    return result


def detect_conflicts(items: list[EvidenceItem]) -> list[EvidenceConflict]:
    """Detect numeric claims sharing a topic, without deciding which is true."""
    grouped: dict[str, list[tuple[str, EvidenceItem]]] = {}
    pattern = re.compile(r"(?P<topic>[a-z][a-z\s-]{2,40}?)(?:\s+is|\s+of|:)?\s*\$?(?P<value>\d+(?:\.\d+)?\s*(?:%|/\s*(?:order|delivery)|per\s+(?:order|delivery))?)", re.I)
    for item in items:
        if not item.content:
            continue
        for match in pattern.finditer(item.content):
            topic = re.sub(r"\s+", " ", match.group("topic").strip().lower())
            if len(topic) < 3:
                continue
            value = re.sub(r"\s+", " ", match.group("value")).strip()
            grouped.setdefault(topic, []).append((value, item))
    conflicts = []
    for topic, claims in grouped.items():
        values = list(dict.fromkeys(value for value, _ in claims))
        if len(values) > 1:
            conflicts.append(EvidenceConflict(topic=topic, evidence_ids=[item.id for _, item in claims], values=values, message=f"Conflicting persisted values for {topic}: {', '.join(values)}"))
    return conflicts
