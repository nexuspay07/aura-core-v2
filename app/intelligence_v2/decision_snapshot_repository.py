"""Tenant-scoped insert-only persistence for canonical Decision snapshots."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from uuid import uuid4
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from app.db.decision_execution_snapshot_table import decision_execution_snapshot_table
from app.db.intelligence_session_table import intelligence_session_table
from app.intelligence_v2.decision_snapshot import CanonicalDecisionSnapshotV1

class DecisionSnapshotUnavailableError(LookupError): pass

@dataclass(frozen=True)
class PersistedDecisionSnapshot:
    id: int
    public_id: str
    intelligence_session_id: int | None
    user_id: int
    organization_id: int
    workspace_id: int
    snapshot_version: int
    snapshot: CanonicalDecisionSnapshotV1

class DecisionExecutionSnapshotRepository:
    @staticmethod
    def _record(row) -> PersistedDecisionSnapshot:
        return PersistedDecisionSnapshot(id=row["id"], public_id=row["public_id"], intelligence_session_id=row["intelligence_session_id"], user_id=row["user_id"], organization_id=row["organization_id"], workspace_id=row["workspace_id"], snapshot_version=row["snapshot_version"], snapshot=CanonicalDecisionSnapshotV1.from_dict(row["canonical_decision_json"]))

    def create(self, db, *, snapshot: CanonicalDecisionSnapshotV1, intelligence_session_id: int, user_id: int, organization_id: int, workspace_id: int) -> PersistedDecisionSnapshot:
        if not isinstance(snapshot, CanonicalDecisionSnapshotV1): raise TypeError("canonical snapshot required")
        owned_session = db.execute(select(intelligence_session_table.c.id).where(
            intelligence_session_table.c.id == intelligence_session_id,
            intelligence_session_table.c.created_by_user_id == user_id,
            intelligence_session_table.c.organization_id == organization_id,
            intelligence_session_table.c.workspace_id == workspace_id,
            intelligence_session_table.c.is_active.is_(True),
        )).first()
        if not owned_session:
            raise DecisionSnapshotUnavailableError("authorized source session unavailable")
        for _ in range(3):
            version = db.execute(select(func.coalesce(func.max(decision_execution_snapshot_table.c.snapshot_version), 0) + 1).where(decision_execution_snapshot_table.c.intelligence_session_id == intelligence_session_id)).scalar_one()
            try:
                with db.begin_nested():
                    result = db.execute(decision_execution_snapshot_table.insert().values(public_id=str(uuid4()), intelligence_session_id=intelligence_session_id, user_id=user_id, organization_id=organization_id, workspace_id=workspace_id, snapshot_version=version, snapshot_schema_version=snapshot.schema_version, canonical_decision_json=snapshot.to_dict()))
                return self.get_owned(db, snapshot_id=result.inserted_primary_key[0], user_id=user_id, organization_id=organization_id, workspace_id=workspace_id)
            except IntegrityError:
                continue
        raise DecisionSnapshotUnavailableError("concurrent snapshot version allocation could not be completed")

    def get_owned(self, db, *, snapshot_id: int, user_id: int, organization_id: int, workspace_id: int) -> PersistedDecisionSnapshot:
        row = db.execute(select(decision_execution_snapshot_table).where(decision_execution_snapshot_table.c.id == snapshot_id, decision_execution_snapshot_table.c.user_id == user_id, decision_execution_snapshot_table.c.organization_id == organization_id, decision_execution_snapshot_table.c.workspace_id == workspace_id)).mappings().first()
        if not row: raise DecisionSnapshotUnavailableError("canonical Decision snapshot unavailable")
        return self._record(row)

    def get_by_public_id_owned(self, db, *, public_id: str, user_id: int, organization_id: int, workspace_id: int) -> PersistedDecisionSnapshot:
        row = db.execute(select(decision_execution_snapshot_table).where(decision_execution_snapshot_table.c.public_id == public_id, decision_execution_snapshot_table.c.user_id == user_id, decision_execution_snapshot_table.c.organization_id == organization_id, decision_execution_snapshot_table.c.workspace_id == workspace_id)).mappings().first()
        if not row: raise DecisionSnapshotUnavailableError("canonical Decision snapshot unavailable")
        return self._record(row)

    def latest_for_session_owned(self, db, *, intelligence_session_id: int, user_id: int, organization_id: int, workspace_id: int) -> PersistedDecisionSnapshot | None:
        row = db.execute(select(decision_execution_snapshot_table).where(decision_execution_snapshot_table.c.intelligence_session_id == intelligence_session_id, decision_execution_snapshot_table.c.user_id == user_id, decision_execution_snapshot_table.c.organization_id == organization_id, decision_execution_snapshot_table.c.workspace_id == workspace_id).order_by(decision_execution_snapshot_table.c.snapshot_version.desc()).limit(1)).mappings().first()
        return self._record(row) if row else None

decision_execution_snapshot_repository = DecisionExecutionSnapshotRepository()
