"""Durable, privacy-safe coordination for Simulation creation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from app.db.simulation_idempotency_table import simulation_create_idempotency_table
from app.db.simulation_resource_table import simulation_resource_table
from app.db.workspace_table import workspace_table
from app.strategy.contracts import StrategyScope


SIMULATION_CREATE_OPERATION = "simulation_create_strategy_stress_test"
IDEMPOTENCY_KEY_MAX_LENGTH = 255
CLAIM_LEASE_DURATION = timedelta(minutes=5)
MAX_CLAIM_LEASE_DURATION = timedelta(minutes=15)


class SimulationIdempotencyError(ValueError):
    pass


class SimulationIdempotencyCompletionError(SimulationIdempotencyError):
    pass


class SimulationCreateClaimState(str, Enum):
    CLAIMED = "CLAIMED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CONFLICT = "CONFLICT"


@dataclass(frozen=True)
class SimulationCreateClaim:
    state: SimulationCreateClaimState
    claim_token: str | None = None
    simulation_resource_id: int | None = None


class SimulationCreateIdempotencyStore:
    """Claim and complete Simulation creation across backend workers."""

    @staticmethod
    def _lease_duration(value: timedelta) -> timedelta:
        if not isinstance(value, timedelta) or not timedelta(0) < value <= MAX_CLAIM_LEASE_DURATION:
            raise SimulationIdempotencyError("Simulation claim lease duration is invalid")
        return value

    @staticmethod
    def _key(value: object) -> str:
        key = value.strip() if isinstance(value, str) else ""
        if not key or len(key) > IDEMPOTENCY_KEY_MAX_LENGTH:
            raise SimulationIdempotencyError("Idempotency key must contain 1 to 255 characters")
        return key

    @staticmethod
    def _fingerprint(value: object) -> str:
        if not isinstance(value, str) or len(value) != 64:
            raise SimulationIdempotencyError("Request fingerprint must be a SHA-256 digest")
        try:
            int(value, 16)
        except ValueError as error:
            raise SimulationIdempotencyError("Request fingerprint must be a SHA-256 digest") from error
        return value.lower()

    @staticmethod
    def _actor(actor_user_id: int, scope: StrategyScope) -> None:
        if (
            not isinstance(actor_user_id, int)
            or isinstance(actor_user_id, bool)
            or actor_user_id <= 0
            or not isinstance(scope, StrategyScope)
            or scope.user_id != actor_user_id
        ):
            raise SimulationIdempotencyError("Authenticated Simulation scope is invalid")

    @staticmethod
    def _tenancy(scope: StrategyScope) -> dict[str, int | None]:
        if scope.organization_id is None and scope.workspace_id is None:
            return {"owner_user_id": scope.user_id, "organization_id": None, "workspace_id": None}
        if scope.organization_id is None or scope.workspace_id is None:
            raise SimulationIdempotencyError("Simulation scope must be personal or complete workspace scope")
        return {"owner_user_id": None, "organization_id": scope.organization_id, "workspace_id": scope.workspace_id}

    @staticmethod
    def _conditions(*, actor_user_id: int, scope: StrategyScope, key: str):
        conditions = [
            simulation_create_idempotency_table.c.actor_user_id == actor_user_id,
            simulation_create_idempotency_table.c.operation == SIMULATION_CREATE_OPERATION,
            simulation_create_idempotency_table.c.idempotency_key == key,
        ]
        if scope.organization_id is None:
            conditions.extend([
                simulation_create_idempotency_table.c.owner_user_id == scope.user_id,
                simulation_create_idempotency_table.c.organization_id.is_(None),
                simulation_create_idempotency_table.c.workspace_id.is_(None),
            ])
        else:
            conditions.extend([
                simulation_create_idempotency_table.c.owner_user_id.is_(None),
                simulation_create_idempotency_table.c.organization_id == scope.organization_id,
                simulation_create_idempotency_table.c.workspace_id == scope.workspace_id,
            ])
        return tuple(conditions)

    def claim(
        self, db, *, idempotency_key: str, request_fingerprint: str,
        actor_user_id: int, scope: StrategyScope, now: datetime | None = None,
        lease_duration: timedelta = CLAIM_LEASE_DURATION,
    ) -> SimulationCreateClaim:
        self._actor(actor_user_id, scope)
        key = self._key(idempotency_key)
        fingerprint = self._fingerprint(request_fingerprint)
        lease_duration = self._lease_duration(lease_duration)
        tenancy = self._tenancy(scope)
        if scope.organization_id is not None and not db.execute(select(workspace_table.c.id).where(
            workspace_table.c.id == scope.workspace_id,
            workspace_table.c.organization_id == scope.organization_id,
        )).first():
            raise SimulationIdempotencyError("Workspace does not belong to the Simulation organization")
        claimed_at = now or datetime.now(timezone.utc)
        token = str(uuid4())
        try:
            with db.begin_nested():
                db.execute(simulation_create_idempotency_table.insert().values(
                    idempotency_key=key, operation=SIMULATION_CREATE_OPERATION,
                    request_fingerprint=fingerprint, actor_user_id=actor_user_id,
                    status="in_progress", claim_token=token,
                    lease_expires_at=claimed_at + lease_duration,
                    updated_at=claimed_at, **tenancy,
                ))
            return SimulationCreateClaim(SimulationCreateClaimState.CLAIMED, claim_token=token)
        except IntegrityError:
            pass

        conditions = self._conditions(actor_user_id=actor_user_id, scope=scope, key=key)
        row = db.execute(select(simulation_create_idempotency_table).where(*conditions)).mappings().one()
        if row["request_fingerprint"] != fingerprint:
            return SimulationCreateClaim(SimulationCreateClaimState.CONFLICT)
        if row["status"] == "completed":
            return SimulationCreateClaim(
                SimulationCreateClaimState.COMPLETED,
                simulation_resource_id=row["simulation_resource_id"],
            )
        lease = row["lease_expires_at"]
        if lease.tzinfo is None:
            lease = lease.replace(tzinfo=timezone.utc)
        if lease > claimed_at:
            return SimulationCreateClaim(SimulationCreateClaimState.IN_PROGRESS)
        reclaimed = db.execute(update(simulation_create_idempotency_table).where(
            simulation_create_idempotency_table.c.id == row["id"],
            simulation_create_idempotency_table.c.status == "in_progress",
            simulation_create_idempotency_table.c.claim_token == row["claim_token"],
            simulation_create_idempotency_table.c.lease_expires_at == row["lease_expires_at"],
        ).values(
            claim_token=token, lease_expires_at=claimed_at + lease_duration,
            updated_at=claimed_at,
        ))
        if reclaimed.rowcount == 1:
            return SimulationCreateClaim(SimulationCreateClaimState.CLAIMED, claim_token=token)
        return SimulationCreateClaim(SimulationCreateClaimState.IN_PROGRESS)

    def renew_claim(
        self, db, *, idempotency_key: str, actor_user_id: int,
        scope: StrategyScope, claim_token: str, now: datetime | None = None,
        lease_duration: timedelta = CLAIM_LEASE_DURATION,
    ) -> bool:
        self._actor(actor_user_id, scope)
        key = self._key(idempotency_key)
        lease_duration = self._lease_duration(lease_duration)
        renewed_at = now or datetime.now(timezone.utc)
        changed = db.execute(update(simulation_create_idempotency_table).where(
            *self._conditions(actor_user_id=actor_user_id, scope=scope, key=key),
            simulation_create_idempotency_table.c.status == "in_progress",
            simulation_create_idempotency_table.c.claim_token == claim_token,
            simulation_create_idempotency_table.c.lease_expires_at > renewed_at,
        ).values(
            lease_expires_at=renewed_at + lease_duration, updated_at=renewed_at,
        ))
        return changed.rowcount == 1

    def release_claim(
        self, db, *, idempotency_key: str, actor_user_id: int,
        scope: StrategyScope, claim_token: str, now: datetime | None = None,
    ) -> bool:
        self._actor(actor_user_id, scope)
        key = self._key(idempotency_key)
        released_at = now or datetime.now(timezone.utc)
        changed = db.execute(update(simulation_create_idempotency_table).where(
            *self._conditions(actor_user_id=actor_user_id, scope=scope, key=key),
            simulation_create_idempotency_table.c.status == "in_progress",
            simulation_create_idempotency_table.c.claim_token == claim_token,
        ).values(lease_expires_at=released_at, updated_at=released_at))
        return changed.rowcount == 1

    def complete(
        self, db, *, idempotency_key: str, request_fingerprint: str,
        actor_user_id: int, scope: StrategyScope, claim_token: str,
        simulation_resource_id: int, now: datetime | None = None,
    ) -> SimulationCreateClaim:
        self._actor(actor_user_id, scope)
        key = self._key(idempotency_key)
        fingerprint = self._fingerprint(request_fingerprint)
        completed_at = now or datetime.now(timezone.utc)
        conditions = self._conditions(actor_user_id=actor_user_id, scope=scope, key=key)
        resource_conditions = [simulation_resource_table.c.id == simulation_resource_id]
        if scope.organization_id is None:
            resource_conditions.extend([
                simulation_resource_table.c.owner_user_id == scope.user_id,
                simulation_resource_table.c.organization_id.is_(None),
                simulation_resource_table.c.workspace_id.is_(None),
            ])
        else:
            resource_conditions.extend([
                simulation_resource_table.c.owner_user_id.is_(None),
                simulation_resource_table.c.organization_id == scope.organization_id,
                simulation_resource_table.c.workspace_id == scope.workspace_id,
            ])
        if not isinstance(simulation_resource_id, int) or isinstance(simulation_resource_id, bool) or not db.execute(
            select(simulation_resource_table.c.id).where(*resource_conditions)
        ).first():
            raise SimulationIdempotencyCompletionError("Completed Simulation resource is invalid")
        locked = db.execute(update(simulation_create_idempotency_table).where(
            *conditions,
            simulation_create_idempotency_table.c.status == "in_progress",
            simulation_create_idempotency_table.c.request_fingerprint == fingerprint,
            simulation_create_idempotency_table.c.claim_token == claim_token,
            simulation_create_idempotency_table.c.lease_expires_at > completed_at,
        ).values(updated_at=simulation_create_idempotency_table.c.updated_at))
        if locked.rowcount != 1:
            raise SimulationIdempotencyCompletionError("Simulation idempotency claim cannot be completed")
        completed = db.execute(update(simulation_create_idempotency_table).where(
            *conditions,
            simulation_create_idempotency_table.c.status == "in_progress",
            simulation_create_idempotency_table.c.request_fingerprint == fingerprint,
            simulation_create_idempotency_table.c.claim_token == claim_token,
            simulation_create_idempotency_table.c.lease_expires_at > completed_at,
        ).values(
            status="completed", simulation_resource_id=simulation_resource_id,
            claim_token=None, lease_expires_at=None, updated_at=completed_at,
        ))
        if completed.rowcount != 1:
            raise SimulationIdempotencyCompletionError("Simulation idempotency completion conflicted")
        return SimulationCreateClaim(
            SimulationCreateClaimState.COMPLETED,
            simulation_resource_id=simulation_resource_id,
        )


simulation_create_idempotency_store = SimulationCreateIdempotencyStore()
