"""Tenant-safe persistence for canonical Strategy resources and revisions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping
from uuid import uuid4

from sqlalchemy import select, update

from app.db.personal_decision_table import personal_decision_table
from app.db.strategy_resource_table import strategy_resource_table, strategy_revision_table
from app.db.workspace_table import workspace_table
from app.strategy.contracts import (
    ConfidenceLevel,
    EvidenceReference,
    StrategyAlternative,
    StrategyAssumption,
    StrategyConstraint,
    StrategyPhase,
    StrategyResource,
    StrategyResult,
    StrategyRisk,
    StrategyScope,
    SuccessMeasure,
)
from app.strategy.validation import StrategyValidationError, validate_strategy_result


SNAPSHOT_SCHEMA_VERSION = 1
ORIGIN_TYPES = frozenset({"direct", "decision_derived"})
_SNAPSHOT_FIELDS = frozenset({
    "objective", "chosen_direction", "approach", "phases", "success_measures",
    "change_conditions", "confidence", "confidence_rationale", "source_reference",
    "constraints", "assumptions", "resources", "risks", "alternatives",
    "uncertainties", "evidence_refs", "time_horizon",
})


class StrategyPersistenceError(ValueError):
    """Persisted Strategy input or data violates the durable contract."""


class StrategyPersistenceNotFoundError(StrategyPersistenceError):
    """No Strategy exists in the authorized tenant scope."""


class StrategyPersistenceConflictError(StrategyPersistenceError):
    """A Strategy metadata mutation used a stale optimistic lock."""


@dataclass(frozen=True)
class PersistedStrategy:
    public_id: str
    title: str
    scope: StrategyScope
    created_by_user_id: int
    current_revision_number: int
    lock_version: int
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime
    origin_type: str
    source_decision_id: int | None
    result: StrategyResult


def serialize_strategy_result(result: StrategyResult) -> dict[str, Any]:
    """Serialize canonical intelligence without durable identity or tenant authority."""

    try:
        validate_strategy_result(result)
    except StrategyValidationError as error:
        raise StrategyPersistenceError("StrategyResult is not valid canonical intelligence") from error
    return {
        "objective": result.objective,
        "chosen_direction": result.chosen_direction,
        "approach": result.approach,
        "phases": [
            {
                "order": item.order,
                "name": item.name,
                "purpose": item.purpose,
                "focus_areas": list(item.focus_areas),
                "milestone_intent": item.milestone_intent,
            }
            for item in result.phases
        ],
        "success_measures": [
            {"condition": item.condition, "evidence_ref": item.evidence_ref}
            for item in result.success_measures
        ],
        "change_conditions": list(result.change_conditions),
        "confidence": result.confidence.value,
        "confidence_rationale": list(result.confidence_rationale),
        "source_reference": result.source_reference,
        "constraints": [
            {"constraint_id": item.constraint_id, "statement": item.statement}
            for item in result.constraints
        ],
        "assumptions": [
            {"statement": item.statement, "source": item.source}
            for item in result.assumptions
        ],
        "resources": [
            {"name": item.name, "description": item.description}
            for item in result.resources
        ],
        "risks": [
            {"risk": item.risk, "mitigation": item.mitigation}
            for item in result.risks
        ],
        "alternatives": [
            {"name": item.name, "approach": item.approach}
            for item in result.alternatives
        ],
        "uncertainties": list(result.uncertainties),
        "evidence_refs": [
            {"evidence_id": item.evidence_id, "citation_label": item.citation_label}
            for item in result.evidence_refs
        ],
        "time_horizon": result.time_horizon,
    }


def normalize_strategy_title(value: object) -> str:
    """Normalize trusted product metadata without invoking intelligence."""

    title = " ".join(value.split()) if isinstance(value, str) else ""
    if not title or len(title) > 255:
        raise StrategyPersistenceError("Strategy title must contain 1 to 255 characters")
    return title


def _object(value: object, name: str, fields: set[str]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != fields:
        raise StrategyPersistenceError(f"Malformed Strategy snapshot: {name}")
    return value


def _list(value: object, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise StrategyPersistenceError(f"Malformed Strategy snapshot: {name}")
    return value


def _optional_text(value: object, name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise StrategyPersistenceError(f"Malformed Strategy snapshot: {name}")
    return value


def hydrate_strategy_result(
    snapshot: object,
    *,
    scope: StrategyScope,
    public_id: str,
    revision_number: int,
    source_decision_id: int | None,
    snapshot_schema_version: int,
) -> StrategyResult:
    """Hydrate validated canonical intelligence using authoritative row metadata."""

    if snapshot_schema_version != SNAPSHOT_SCHEMA_VERSION:
        raise StrategyPersistenceError("Unsupported Strategy snapshot schema version")
    root = _object(snapshot, "root", set(_SNAPSHOT_FIELDS))
    try:
        phases = tuple(
            StrategyPhase(
                order=item["order"],
                name=item["name"],
                purpose=item["purpose"],
                focus_areas=tuple(_list(item["focus_areas"], "phase.focus_areas")),
                milestone_intent=_optional_text(item["milestone_intent"], "phase.milestone_intent"),
            )
            for raw in _list(root["phases"], "phases")
            for item in [_object(raw, "phase", {"order", "name", "purpose", "focus_areas", "milestone_intent"})]
        )
        result = StrategyResult(
            scope=scope,
            strategy_id=public_id,
            version=revision_number,
            source_decision_id=source_decision_id,
            source_reference=_optional_text(root["source_reference"], "source_reference"),
            objective=root["objective"],
            chosen_direction=root["chosen_direction"],
            approach=root["approach"],
            phases=phases,
            success_measures=tuple(
                SuccessMeasure(item["condition"], _optional_text(item["evidence_ref"], "success_measure.evidence_ref"))
                for raw in _list(root["success_measures"], "success_measures")
                for item in [_object(raw, "success_measure", {"condition", "evidence_ref"})]
            ),
            change_conditions=tuple(_list(root["change_conditions"], "change_conditions")),
            confidence=ConfidenceLevel(root["confidence"]),
            confidence_rationale=tuple(_list(root["confidence_rationale"], "confidence_rationale")),
            constraints=tuple(
                StrategyConstraint(item["constraint_id"], item["statement"])
                for raw in _list(root["constraints"], "constraints")
                for item in [_object(raw, "constraint", {"constraint_id", "statement"})]
            ),
            assumptions=tuple(
                StrategyAssumption(item["statement"], item["source"])
                for raw in _list(root["assumptions"], "assumptions")
                for item in [_object(raw, "assumption", {"statement", "source"})]
            ),
            resources=tuple(
                StrategyResource(item["name"], item["description"])
                for raw in _list(root["resources"], "resources")
                for item in [_object(raw, "resource", {"name", "description"})]
            ),
            risks=tuple(
                StrategyRisk(item["risk"], _optional_text(item["mitigation"], "risk.mitigation"))
                for raw in _list(root["risks"], "risks")
                for item in [_object(raw, "risk", {"risk", "mitigation"})]
            ),
            alternatives=tuple(
                StrategyAlternative(item["name"], item["approach"])
                for raw in _list(root["alternatives"], "alternatives")
                for item in [_object(raw, "alternative", {"name", "approach"})]
            ),
            uncertainties=tuple(_list(root["uncertainties"], "uncertainties")),
            evidence_refs=tuple(
                EvidenceReference(item["evidence_id"], _optional_text(item["citation_label"], "evidence.citation_label"))
                for raw in _list(root["evidence_refs"], "evidence_refs")
                for item in [_object(raw, "evidence", {"evidence_id", "citation_label"})]
            ),
            time_horizon=_optional_text(root["time_horizon"], "time_horizon"),
        )
        validate_strategy_result(result)
    except StrategyPersistenceError:
        raise
    except (KeyError, TypeError, ValueError, StrategyValidationError) as error:
        raise StrategyPersistenceError("Malformed Strategy snapshot") from error
    return result


class StrategyRepository:
    """Create and retrieve Strategies only within explicit authorized scopes."""

    @staticmethod
    def _title(value: str) -> str:
        return normalize_strategy_title(value)

    @staticmethod
    def _validate_scope(db, scope: StrategyScope) -> dict[str, int | None]:
        if scope.organization_id is None and scope.workspace_id is None:
            return {"owner_user_id": scope.user_id, "organization_id": None, "workspace_id": None}
        if scope.organization_id is None or scope.workspace_id is None:
            raise StrategyPersistenceError("Strategy scope must be personal or a complete workspace scope")
        workspace = db.execute(
            select(workspace_table.c.id).where(
                workspace_table.c.id == scope.workspace_id,
                workspace_table.c.organization_id == scope.organization_id,
            )
        ).first()
        if not workspace:
            raise StrategyPersistenceError("Workspace does not belong to the Strategy organization")
        return {
            "owner_user_id": None,
            "organization_id": scope.organization_id,
            "workspace_id": scope.workspace_id,
        }

    @staticmethod
    def _validate_source_decision(db, result: StrategyResult, created_by_user_id: int, origin_type: str) -> int | None:
        source_id = result.source_decision_id
        if origin_type == "direct":
            if source_id is not None:
                raise StrategyPersistenceError("Direct Strategies cannot reference a source Decision")
            return None
        if source_id is None:
            return None
        conditions = [
            personal_decision_table.c.id == source_id,
            personal_decision_table.c.user_id == created_by_user_id,
        ]
        if result.scope.organization_id is not None:
            conditions.extend([
                personal_decision_table.c.organization_id == result.scope.organization_id,
                personal_decision_table.c.workspace_id == result.scope.workspace_id,
            ])
        if not db.execute(select(personal_decision_table.c.id).where(*conditions)).first():
            raise StrategyPersistenceError("Source Decision is not authorized for this Strategy")
        return source_id

    def create_strategy(
        self,
        db,
        *,
        result: StrategyResult,
        title: str,
        created_by_user_id: int,
        origin_type: str,
    ) -> PersistedStrategy:
        if origin_type not in ORIGIN_TYPES:
            raise StrategyPersistenceError("Unsupported Strategy origin type")
        normalized_title = self._title(title)
        snapshot = serialize_strategy_result(result)
        tenancy = self._validate_scope(db, result.scope)
        source_decision_id = self._validate_source_decision(db, result, created_by_user_id, origin_type)
        public_id = str(uuid4())
        with db.begin_nested():
            resource_insert = db.execute(strategy_resource_table.insert().values(
                public_id=public_id,
                title=normalized_title,
                created_by_user_id=created_by_user_id,
                current_revision_number=1,
                lock_version=1,
                **tenancy,
            ))
            strategy_id = resource_insert.inserted_primary_key[0]
            db.execute(strategy_revision_table.insert().values(
                strategy_id=strategy_id,
                revision_number=1,
                canonical_result_json=snapshot,
                snapshot_schema_version=SNAPSHOT_SCHEMA_VERSION,
                created_by_user_id=created_by_user_id,
                origin_type=origin_type,
                source_decision_id=source_decision_id,
            ))
        return self._get_by_internal_id(db, strategy_id)

    def get_personal_strategy_by_public_id(
        self, db, *, public_id: str, owner_user_id: int
    ) -> PersistedStrategy:
        resource = db.execute(select(strategy_resource_table).where(
            strategy_resource_table.c.public_id == public_id,
            strategy_resource_table.c.owner_user_id == owner_user_id,
            strategy_resource_table.c.organization_id.is_(None),
            strategy_resource_table.c.workspace_id.is_(None),
        )).mappings().first()
        if not resource:
            raise StrategyPersistenceNotFoundError("Strategy not found")
        return self._hydrate(db, resource)

    def get_workspace_strategy_by_public_id(
        self,
        db,
        *,
        public_id: str,
        organization_id: int,
        workspace_id: int,
    ) -> PersistedStrategy:
        resource = db.execute(select(strategy_resource_table).where(
            strategy_resource_table.c.public_id == public_id,
            strategy_resource_table.c.owner_user_id.is_(None),
            strategy_resource_table.c.organization_id == organization_id,
            strategy_resource_table.c.workspace_id == workspace_id,
        )).mappings().first()
        if not resource:
            raise StrategyPersistenceNotFoundError("Strategy not found")
        return self._hydrate(db, resource)

    def list_personal_strategies(
        self, db, *, owner_user_id: int, limit: int = 50
    ) -> list[PersistedStrategy]:
        return self._list(db, (
            strategy_resource_table.c.owner_user_id == owner_user_id,
            strategy_resource_table.c.organization_id.is_(None),
            strategy_resource_table.c.workspace_id.is_(None),
        ), limit)

    def list_workspace_strategies(
        self, db, *, organization_id: int, workspace_id: int, limit: int = 50
    ) -> list[PersistedStrategy]:
        return self._list(db, (
            strategy_resource_table.c.owner_user_id.is_(None),
            strategy_resource_table.c.organization_id == organization_id,
            strategy_resource_table.c.workspace_id == workspace_id,
        ), limit)

    def archive_personal_strategy(
        self,
        db,
        *,
        public_id: str,
        owner_user_id: int,
        expected_lock_version: int,
    ) -> PersistedStrategy:
        return self._archive(db, (
            strategy_resource_table.c.public_id == public_id,
            strategy_resource_table.c.owner_user_id == owner_user_id,
            strategy_resource_table.c.organization_id.is_(None),
            strategy_resource_table.c.workspace_id.is_(None),
        ), expected_lock_version)

    def archive_workspace_strategy(
        self,
        db,
        *,
        public_id: str,
        organization_id: int,
        workspace_id: int,
        expected_lock_version: int,
    ) -> PersistedStrategy:
        return self._archive(db, (
            strategy_resource_table.c.public_id == public_id,
            strategy_resource_table.c.owner_user_id.is_(None),
            strategy_resource_table.c.organization_id == organization_id,
            strategy_resource_table.c.workspace_id == workspace_id,
        ), expected_lock_version)

    def _list(self, db, conditions: tuple[Any, ...], limit: int) -> list[PersistedStrategy]:
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100:
            raise StrategyPersistenceError("Strategy list limit must be between 1 and 100")
        resources = db.execute(
            select(strategy_resource_table)
            .where(*conditions, strategy_resource_table.c.archived_at.is_(None))
            .order_by(strategy_resource_table.c.updated_at.desc(), strategy_resource_table.c.id.desc())
            .limit(limit)
        ).mappings().all()
        return [self._hydrate(db, resource) for resource in resources]

    def _archive(
        self, db, conditions: tuple[Any, ...], expected_lock_version: int
    ) -> PersistedStrategy:
        if (
            not isinstance(expected_lock_version, int)
            or isinstance(expected_lock_version, bool)
            or expected_lock_version <= 0
        ):
            raise StrategyPersistenceError("Expected lock version must be a positive integer")
        resource = db.execute(select(strategy_resource_table).where(*conditions)).mappings().first()
        if not resource:
            raise StrategyPersistenceNotFoundError("Strategy not found")
        if resource["archived_at"] is not None:
            return self._hydrate(db, resource)

        now = datetime.now(timezone.utc)
        changed = db.execute(
            update(strategy_resource_table)
            .where(
                strategy_resource_table.c.id == resource["id"],
                strategy_resource_table.c.archived_at.is_(None),
                strategy_resource_table.c.lock_version == expected_lock_version,
            )
            .values(
                archived_at=now,
                updated_at=now,
                lock_version=strategy_resource_table.c.lock_version + 1,
            )
        )
        if changed.rowcount != 1:
            current = db.execute(
                select(strategy_resource_table).where(strategy_resource_table.c.id == resource["id"])
            ).mappings().one()
            if current["archived_at"] is not None:
                return self._hydrate(db, current)
            raise StrategyPersistenceConflictError("Strategy lock version is stale")
        return self._get_by_internal_id(db, resource["id"])

    def _get_by_internal_id(self, db, strategy_id: int) -> PersistedStrategy:
        resource = db.execute(
            select(strategy_resource_table).where(strategy_resource_table.c.id == strategy_id)
        ).mappings().one()
        return self._hydrate(db, resource)

    @staticmethod
    def _hydrate(db, resource: Mapping[str, Any]) -> PersistedStrategy:
        revision = db.execute(select(strategy_revision_table).where(
            strategy_revision_table.c.strategy_id == resource["id"],
            strategy_revision_table.c.revision_number == resource["current_revision_number"],
        )).mappings().first()
        if not revision:
            raise StrategyPersistenceError("Strategy current revision is missing")
        scope = StrategyScope(
            user_id=resource["owner_user_id"] or resource["created_by_user_id"],
            organization_id=resource["organization_id"],
            workspace_id=resource["workspace_id"],
        )
        result = hydrate_strategy_result(
            revision["canonical_result_json"],
            scope=scope,
            public_id=resource["public_id"],
            revision_number=revision["revision_number"],
            source_decision_id=revision["source_decision_id"],
            snapshot_schema_version=revision["snapshot_schema_version"],
        )
        return PersistedStrategy(
            public_id=resource["public_id"],
            title=resource["title"],
            scope=scope,
            created_by_user_id=resource["created_by_user_id"],
            current_revision_number=resource["current_revision_number"],
            lock_version=resource["lock_version"],
            archived_at=resource["archived_at"],
            created_at=resource["created_at"],
            updated_at=resource["updated_at"],
            origin_type=revision["origin_type"],
            source_decision_id=revision["source_decision_id"],
            result=result,
        )


strategy_repository = StrategyRepository()
