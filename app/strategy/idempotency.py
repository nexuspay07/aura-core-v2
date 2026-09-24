"""Durable, privacy-safe coordination for direct Strategy creation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from hashlib import sha256
import json
from typing import Any
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from app.db.strategy_idempotency_table import strategy_create_idempotency_table
from app.db.strategy_resource_table import strategy_resource_table
from app.strategy.contracts import StrategyInput, StrategyResult, StrategyScope
from app.strategy.persistence import PersistedStrategy, StrategyRepository, normalize_strategy_title, strategy_repository
from app.strategy.validation import StrategyValidationError, validate_strategy_input


STRATEGY_CREATE_OPERATION = "strategy_create_direct"
STRATEGY_CREATE_FROM_DECISION_OPERATION = "strategy_create_from_decision"
IDEMPOTENCY_KEY_MAX_LENGTH = 255
CLAIM_LEASE_DURATION = timedelta(minutes=5)


class StrategyIdempotencyError(ValueError):
    pass


class StrategyIdempotencyCompletionError(StrategyIdempotencyError):
    pass


class StrategyCreateClaimState(str, Enum):
    CLAIMED = "CLAIMED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CONFLICT = "CONFLICT"

class StrategyCreateOperation(str, Enum):
    DIRECT = STRATEGY_CREATE_OPERATION
    FROM_DECISION = STRATEGY_CREATE_FROM_DECISION_OPERATION


@dataclass(frozen=True)
class StrategyCreateClaim:
    state: StrategyCreateClaimState
    claim_token: str | None = None
    strategy_resource_id: int | None = None


def _json_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return value


def strategy_create_request_fingerprint(*, title: str, strategy_input: StrategyInput) -> str:
    """Hash the normalized effective direct-create request, never its HTTP envelope."""

    normalized_title = normalize_strategy_title(title)
    try:
        validate_strategy_input(strategy_input)
    except StrategyValidationError as error:
        raise StrategyIdempotencyError("Invalid canonical Strategy input") from error
    if strategy_input.source_decision_id is not None:
        raise StrategyIdempotencyError("Direct Strategy input cannot reference a source Decision")
    payload = {
        "operation": STRATEGY_CREATE_OPERATION,
        "title": normalized_title,
        "strategy_input": _json_value(asdict(strategy_input)),
    }
    canonical = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return sha256(canonical.encode("utf-8")).hexdigest()

def strategy_create_from_decision_fingerprint(*, title: str, strategy_input: StrategyInput, personal_decision_public_id: str, snapshot_public_id: str, snapshot_version: int) -> str:
    normalized_title = normalize_strategy_title(title)
    try: validate_strategy_input(strategy_input)
    except StrategyValidationError as error: raise StrategyIdempotencyError("Invalid canonical Strategy input") from error
    identifiers = (personal_decision_public_id, snapshot_public_id)
    if any(not isinstance(item, str) or not item.strip() for item in identifiers) or not isinstance(snapshot_version, int) or snapshot_version <= 0:
        raise StrategyIdempotencyError("Decision provenance must be complete")
    payload = {"operation": STRATEGY_CREATE_FROM_DECISION_OPERATION, "scope": _json_value(asdict(strategy_input.scope)), "personal_decision_public_id": personal_decision_public_id.strip(), "snapshot_public_id": snapshot_public_id.strip(), "snapshot_version": snapshot_version, "title": normalized_title, "strategy_input": _json_value(asdict(strategy_input))}
    return sha256(json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")).hexdigest()


class StrategyCreateIdempotencyRepository:
    """Claim and complete direct Strategy creation across backend workers."""

    @staticmethod
    def _operation(value: object) -> StrategyCreateOperation:
        if isinstance(value, StrategyCreateOperation): return value
        try: return StrategyCreateOperation(value)
        except (TypeError, ValueError) as error: raise StrategyIdempotencyError("Unsupported Strategy create operation") from error

    @staticmethod
    def _key(value: object) -> str:
        key = value.strip() if isinstance(value, str) else ""
        if not key or len(key) > IDEMPOTENCY_KEY_MAX_LENGTH:
            raise StrategyIdempotencyError("Idempotency key must contain 1 to 255 characters")
        return key

    @staticmethod
    def _scope(scope: StrategyScope) -> dict[str, int | None]:
        if not isinstance(scope, StrategyScope):
            raise StrategyIdempotencyError("Strategy scope must be canonical")
        if scope.organization_id is None and scope.workspace_id is None:
            return {"owner_user_id": scope.user_id, "organization_id": None, "workspace_id": None}
        if scope.organization_id is None or scope.workspace_id is None:
            raise StrategyIdempotencyError("Strategy scope must be personal or complete workspace scope")
        return {"owner_user_id": None, "organization_id": scope.organization_id, "workspace_id": scope.workspace_id}

    @staticmethod
    def _conditions(*, actor_user_id: int, scope: StrategyScope, key: str, operation: StrategyCreateOperation = StrategyCreateOperation.DIRECT):
        conditions = [
            strategy_create_idempotency_table.c.actor_user_id == actor_user_id,
            strategy_create_idempotency_table.c.operation == operation.value,
            strategy_create_idempotency_table.c.idempotency_key == key,
        ]
        if scope.organization_id is None:
            conditions.extend([
                strategy_create_idempotency_table.c.owner_user_id == scope.user_id,
                strategy_create_idempotency_table.c.organization_id.is_(None),
                strategy_create_idempotency_table.c.workspace_id.is_(None),
            ])
        else:
            conditions.extend([
                strategy_create_idempotency_table.c.owner_user_id.is_(None),
                strategy_create_idempotency_table.c.organization_id == scope.organization_id,
                strategy_create_idempotency_table.c.workspace_id == scope.workspace_id,
            ])
        return tuple(conditions)

    def claim(
        self,
        db,
        *,
        idempotency_key: str,
        request_fingerprint: str,
        actor_user_id: int,
        scope: StrategyScope,
        now: datetime | None = None,
        operation: StrategyCreateOperation = StrategyCreateOperation.DIRECT,
    ) -> StrategyCreateClaim:
        operation = self._operation(operation)
        key = self._key(idempotency_key)
        if not isinstance(request_fingerprint, str) or len(request_fingerprint) != 64:
            raise StrategyIdempotencyError("Request fingerprint must be a SHA-256 digest")
        try:
            int(request_fingerprint, 16)
        except ValueError as error:
            raise StrategyIdempotencyError("Request fingerprint must be a SHA-256 digest") from error
        if not isinstance(actor_user_id, int) or isinstance(actor_user_id, bool) or actor_user_id <= 0:
            raise StrategyIdempotencyError("Actor user ID must be a positive integer")
        tenancy = self._scope(scope)
        claimed_at = now or datetime.now(timezone.utc)
        token = str(uuid4())
        try:
            with db.begin_nested():
                db.execute(strategy_create_idempotency_table.insert().values(
                    idempotency_key=key,
                    operation=operation.value,
                    request_fingerprint=request_fingerprint,
                    actor_user_id=actor_user_id,
                    status="in_progress",
                    claim_token=token,
                    lease_expires_at=claimed_at + CLAIM_LEASE_DURATION,
                    updated_at=claimed_at,
                    **tenancy,
                ))
            return StrategyCreateClaim(StrategyCreateClaimState.CLAIMED, claim_token=token)
        except IntegrityError:
            pass

        conditions = self._conditions(actor_user_id=actor_user_id, scope=scope, key=key, operation=operation)
        row = db.execute(select(strategy_create_idempotency_table).where(*conditions)).mappings().one()
        if row["request_fingerprint"] != request_fingerprint:
            return StrategyCreateClaim(StrategyCreateClaimState.CONFLICT)
        if row["status"] == "completed":
            return StrategyCreateClaim(
                StrategyCreateClaimState.COMPLETED,
                strategy_resource_id=row["strategy_resource_id"],
            )
        lease = row["lease_expires_at"]
        if lease.tzinfo is None:
            lease = lease.replace(tzinfo=timezone.utc)
        if lease > claimed_at:
            return StrategyCreateClaim(StrategyCreateClaimState.IN_PROGRESS)

        reclaimed = db.execute(
            update(strategy_create_idempotency_table)
            .where(
                strategy_create_idempotency_table.c.id == row["id"],
                strategy_create_idempotency_table.c.status == "in_progress",
                strategy_create_idempotency_table.c.claim_token == row["claim_token"],
                strategy_create_idempotency_table.c.lease_expires_at == row["lease_expires_at"],
            )
            .values(
                claim_token=token,
                lease_expires_at=claimed_at + CLAIM_LEASE_DURATION,
                updated_at=claimed_at,
            )
        )
        if reclaimed.rowcount == 1:
            return StrategyCreateClaim(StrategyCreateClaimState.CLAIMED, claim_token=token)
        return StrategyCreateClaim(StrategyCreateClaimState.IN_PROGRESS)

    def abandon_claim(
        self,
        db,
        *,
        idempotency_key: str,
        actor_user_id: int,
        scope: StrategyScope,
        claim_token: str,
        now: datetime | None = None,
        operation: StrategyCreateOperation = StrategyCreateOperation.DIRECT,
    ) -> bool:
        operation = self._operation(operation)
        key = self._key(idempotency_key)
        abandoned_at = now or datetime.now(timezone.utc)
        changed = db.execute(
            update(strategy_create_idempotency_table)
            .where(
                *self._conditions(actor_user_id=actor_user_id, scope=scope, key=key, operation=operation),
                strategy_create_idempotency_table.c.status == "in_progress",
                strategy_create_idempotency_table.c.claim_token == claim_token,
            )
            .values(lease_expires_at=abandoned_at, updated_at=abandoned_at)
        )
        return changed.rowcount == 1

    def renew_claim(
        self,
        db,
        *,
        idempotency_key: str,
        actor_user_id: int,
        scope: StrategyScope,
        claim_token: str,
        now: datetime | None = None,
        operation: StrategyCreateOperation = StrategyCreateOperation.DIRECT,
    ) -> bool:
        operation = self._operation(operation)
        """Extend only the current, still-live fenced claim.

        A caller performing a potentially long provider operation can invoke this
        from a separate short transaction. The token predicate prevents a stale
        worker from extending a claim after another worker has reclaimed it.
        """

        key = self._key(idempotency_key)
        renewed_at = now or datetime.now(timezone.utc)
        changed = db.execute(
            update(strategy_create_idempotency_table)
            .where(
                *self._conditions(actor_user_id=actor_user_id, scope=scope, key=key, operation=operation),
                strategy_create_idempotency_table.c.status == "in_progress",
                strategy_create_idempotency_table.c.claim_token == claim_token,
                strategy_create_idempotency_table.c.lease_expires_at > renewed_at,
            )
            .values(
                lease_expires_at=renewed_at + CLAIM_LEASE_DURATION,
                updated_at=renewed_at,
            )
        )
        return changed.rowcount == 1

    def complete_with_strategy(
        self,
        db,
        *,
        idempotency_key: str,
        request_fingerprint: str,
        actor_user_id: int,
        scope: StrategyScope,
        claim_token: str,
        result: StrategyResult,
        title: str,
        origin_type: str = "direct",
        repository: StrategyRepository | None = None,
        now: datetime | None = None,
        operation: StrategyCreateOperation = StrategyCreateOperation.DIRECT,
    ) -> PersistedStrategy:
        operation = self._operation(operation)
        key = self._key(idempotency_key)
        completed_at = now or datetime.now(timezone.utc)
        if result.scope != scope:
            raise StrategyIdempotencyCompletionError("Strategy result scope does not match the idempotency claim")
        storage = repository or strategy_repository
        conditions = self._conditions(actor_user_id=actor_user_id, scope=scope, key=key, operation=operation)
        # Establish the caller-controlled outer write transaction before any
        # savepoint. This also locks/fences the claim on PostgreSQL and avoids
        # SQLite releasing a first savepoint as a durable transaction.
        locked = db.execute(
            update(strategy_create_idempotency_table)
            .where(
                *conditions,
                strategy_create_idempotency_table.c.status == "in_progress",
                strategy_create_idempotency_table.c.request_fingerprint == request_fingerprint,
                strategy_create_idempotency_table.c.claim_token == claim_token,
                strategy_create_idempotency_table.c.lease_expires_at > completed_at,
            )
            .values(updated_at=strategy_create_idempotency_table.c.updated_at)
        )
        if locked.rowcount != 1:
            raise StrategyIdempotencyCompletionError("Idempotency claim cannot be completed")
        with db.begin_nested():
            claim = db.execute(select(strategy_create_idempotency_table).where(
                *conditions,
                strategy_create_idempotency_table.c.status == "in_progress",
                strategy_create_idempotency_table.c.request_fingerprint == request_fingerprint,
                strategy_create_idempotency_table.c.claim_token == claim_token,
                strategy_create_idempotency_table.c.lease_expires_at > completed_at,
            )).mappings().first()
            if not claim:
                raise StrategyIdempotencyCompletionError("Idempotency claim cannot be completed")
            persisted = storage.create_strategy(
                db,
                result=result,
                title=title,
                created_by_user_id=actor_user_id,
                origin_type=origin_type,
            )
            strategy_id = db.execute(select(strategy_resource_table.c.id).where(
                strategy_resource_table.c.public_id == persisted.public_id
            )).scalar_one()
            completed = db.execute(
                update(strategy_create_idempotency_table)
                .where(
                    strategy_create_idempotency_table.c.id == claim["id"],
                    strategy_create_idempotency_table.c.status == "in_progress",
                    strategy_create_idempotency_table.c.claim_token == claim_token,
                    strategy_create_idempotency_table.c.lease_expires_at > completed_at,
                )
                .values(
                    status="completed",
                    strategy_resource_id=strategy_id,
                    claim_token=None,
                    lease_expires_at=None,
                    updated_at=completed_at,
                )
            )
            if completed.rowcount != 1:
                raise StrategyIdempotencyCompletionError("Idempotency completion conflict")
        return persisted


strategy_create_idempotency_repository = StrategyCreateIdempotencyRepository()
