from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event, insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

import app.db.schema  # noqa: F401
from app.db.database import metadata
from app.db.organization_table import organization_table
from app.db.simulation_idempotency_table import simulation_create_idempotency_table
from app.db.simulation_resource_table import simulation_resource_table
from app.db.strategy_resource_table import strategy_resource_table, strategy_revision_table
from app.db.user_table import user_table
from app.db.workspace_table import workspace_table
from app.simulation.idempotency import (
    CLAIM_LEASE_DURATION,
    SIMULATION_CREATE_OPERATION,
    SimulationCreateClaimState,
    SimulationCreateIdempotencyStore,
    SimulationIdempotencyCompletionError,
    SimulationIdempotencyError,
)
from app.strategy.contracts import StrategyScope


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    event.listen(engine, "connect", lambda connection, _: connection.execute("PRAGMA foreign_keys=ON"))
    metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.execute(insert(user_table), [
        {"id": 1, "email": "one@test", "password_hash": "x"},
        {"id": 2, "email": "two@test", "password_hash": "x"},
    ])
    session.execute(insert(organization_table), [
        {"id": 10, "name": "One", "slug": "one", "owner_user_id": 1, "account_type": "business", "plan": "free", "subscription_status": "inactive", "is_active": True},
        {"id": 20, "name": "Two", "slug": "two", "owner_user_id": 2, "account_type": "business", "plan": "free", "subscription_status": "inactive", "is_active": True},
    ])
    session.execute(insert(workspace_table), [
        {"id": 11, "organization_id": 10, "created_by_user_id": 1, "name": "One", "slug": "one-workspace", "workspace_type": "business", "is_active": True},
        {"id": 12, "organization_id": 10, "created_by_user_id": 1, "name": "Other", "slug": "other-workspace", "workspace_type": "business", "is_active": True},
        {"id": 21, "organization_id": 20, "created_by_user_id": 2, "name": "Two", "slug": "two-workspace", "workspace_type": "business", "is_active": True},
    ])
    session.commit()
    yield session
    session.close()
    engine.dispose()


def insert_simulation_resource(db, scope, suffix):
    strategy = db.execute(insert(strategy_resource_table).values(
        public_id=f"00000000-0000-4000-8000-{suffix:012d}", title="Strategy",
        created_by_user_id=scope.user_id,
        owner_user_id=scope.user_id if scope.organization_id is None else None,
        organization_id=scope.organization_id, workspace_id=scope.workspace_id,
        current_revision_number=1, lock_version=1,
    )).inserted_primary_key[0]
    revision = db.execute(insert(strategy_revision_table).values(
        strategy_id=strategy, revision_number=1, canonical_result_json={},
        snapshot_schema_version=1, created_by_user_id=scope.user_id, origin_type="direct",
    )).inserted_primary_key[0]
    return db.execute(insert(simulation_resource_table).values(
        public_id=f"10000000-0000-4000-8000-{suffix:012d}", title="Simulation",
        simulation_type="strategy_stress_test", created_by_user_id=scope.user_id,
        owner_user_id=scope.user_id if scope.organization_id is None else None,
        organization_id=scope.organization_id, workspace_id=scope.workspace_id,
        source_strategy_id=strategy, source_strategy_revision_id=revision,
        current_run_number=1, lock_version=2,
    )).inserted_primary_key[0]


def claim(store, db, scope, *, key="same-key", fingerprint="a" * 64, now=None):
    return store.claim(
        db, idempotency_key=key, request_fingerprint=fingerprint,
        actor_user_id=scope.user_id, scope=scope, now=now,
    )


def test_first_personal_and_workspace_claims_succeed(db):
    store = SimulationCreateIdempotencyStore()
    personal = claim(store, db, StrategyScope(1), key="personal")
    workspace = claim(store, db, StrategyScope(1, 10, 11), key="workspace")
    assert personal.state is workspace.state is SimulationCreateClaimState.CLAIMED
    assert personal.claim_token != workspace.claim_token


def test_same_key_is_partitioned_across_exact_scopes(db):
    store = SimulationCreateIdempotencyStore()
    scopes = (
        StrategyScope(1), StrategyScope(2), StrategyScope(1, 10, 11),
        StrategyScope(1, 10, 12), StrategyScope(2, 20, 21),
    )
    assert all(claim(store, db, scope).state is SimulationCreateClaimState.CLAIMED for scope in scopes)
    assert len(db.execute(select(simulation_create_idempotency_table)).all()) == 5


def test_same_request_is_in_progress_and_different_fingerprint_conflicts(db):
    store = SimulationCreateIdempotencyStore(); scope = StrategyScope(1)
    first = claim(store, db, scope)
    duplicate = claim(store, db, scope)
    conflict = claim(store, db, scope, fingerprint="b" * 64)
    assert first.state is SimulationCreateClaimState.CLAIMED
    assert duplicate.state is SimulationCreateClaimState.IN_PROGRESS
    assert duplicate.claim_token is None
    assert conflict.state is SimulationCreateClaimState.CONFLICT
    row = db.execute(select(simulation_create_idempotency_table)).mappings().one()
    assert row["request_fingerprint"] == "a" * 64


def test_active_lease_cannot_be_stolen_but_stale_lease_is_reclaimed(db):
    store = SimulationCreateIdempotencyStore(); scope = StrategyScope(1)
    started = datetime(2026, 1, 1, tzinfo=timezone.utc)
    first = claim(store, db, scope, now=started)
    active = claim(store, db, scope, now=started + timedelta(minutes=4))
    recovered = claim(store, db, scope, now=started + CLAIM_LEASE_DURATION + timedelta(seconds=1))
    assert active.state is SimulationCreateClaimState.IN_PROGRESS
    assert recovered.state is SimulationCreateClaimState.CLAIMED
    assert recovered.claim_token != first.claim_token


def test_release_requires_owner_token_and_permits_retry(db):
    store = SimulationCreateIdempotencyStore(); scope = StrategyScope(1)
    started = datetime(2026, 1, 1, tzinfo=timezone.utc)
    first = claim(store, db, scope, now=started)
    assert not store.release_claim(
        db, idempotency_key="same-key", actor_user_id=1, scope=scope,
        claim_token="wrong-token", now=started + timedelta(seconds=1),
    )
    assert store.release_claim(
        db, idempotency_key="same-key", actor_user_id=1, scope=scope,
        claim_token=first.claim_token, now=started + timedelta(seconds=1),
    )
    retry = claim(store, db, scope, now=started + timedelta(seconds=2))
    assert retry.state is SimulationCreateClaimState.CLAIMED
    assert retry.claim_token != first.claim_token


def test_valid_completion_links_exact_simulation_and_replays(db):
    store = SimulationCreateIdempotencyStore(); scope = StrategyScope(1)
    resource_id = insert_simulation_resource(db, scope, 1)
    started = datetime.now(timezone.utc)
    owned = claim(store, db, scope, now=started)
    completed = store.complete(
        db, idempotency_key="same-key", request_fingerprint="a" * 64,
        actor_user_id=1, scope=scope, claim_token=owned.claim_token,
        simulation_resource_id=resource_id, now=started + timedelta(seconds=1),
    )
    replay = claim(store, db, scope, now=started + timedelta(seconds=2))
    assert completed.state is replay.state is SimulationCreateClaimState.COMPLETED
    assert completed.simulation_resource_id == replay.simulation_resource_id == resource_id


def test_completion_rejects_wrong_token_missing_or_cross_scope_resource(db):
    store = SimulationCreateIdempotencyStore(); scope = StrategyScope(1)
    owned = claim(store, db, scope)
    own_resource = insert_simulation_resource(db, scope, 1)
    other_resource = insert_simulation_resource(db, StrategyScope(2), 2)
    for token, resource_id in (("wrong", own_resource), (owned.claim_token, 99999), (owned.claim_token, other_resource)):
        with pytest.raises(SimulationIdempotencyCompletionError):
            store.complete(
                db, idempotency_key="same-key", request_fingerprint="a" * 64,
                actor_user_id=1, scope=scope, claim_token=token,
                simulation_resource_id=resource_id,
            )


def test_completed_record_cannot_be_rebound_or_changed(db):
    store = SimulationCreateIdempotencyStore(); scope = StrategyScope(1)
    first_resource = insert_simulation_resource(db, scope, 1)
    second_resource = insert_simulation_resource(db, scope, 2)
    now = datetime.now(timezone.utc)
    owned = claim(store, db, scope, now=now)
    store.complete(
        db, idempotency_key="same-key", request_fingerprint="a" * 64,
        actor_user_id=1, scope=scope, claim_token=owned.claim_token,
        simulation_resource_id=first_resource, now=now + timedelta(seconds=1),
    )
    with pytest.raises(SimulationIdempotencyCompletionError):
        store.complete(
            db, idempotency_key="same-key", request_fingerprint="a" * 64,
            actor_user_id=1, scope=scope, claim_token=owned.claim_token,
            simulation_resource_id=second_resource, now=now + timedelta(seconds=2),
        )
    assert claim(store, db, scope, fingerprint="b" * 64).state is SimulationCreateClaimState.CONFLICT
    row = db.execute(select(simulation_create_idempotency_table)).mappings().one()
    assert row["simulation_resource_id"] == first_resource
    assert row["request_fingerprint"] == "a" * 64
    assert row["operation"] == SIMULATION_CREATE_OPERATION


def test_workspace_relationship_actor_and_fingerprint_are_validated(db):
    store = SimulationCreateIdempotencyStore()
    with pytest.raises(SimulationIdempotencyError, match="Workspace"):
        claim(store, db, StrategyScope(1, 20, 11))
    with pytest.raises(SimulationIdempotencyError, match="scope"):
        store.claim(
            db, idempotency_key="key", request_fingerprint="a" * 64,
            actor_user_id=2, scope=StrategyScope(1),
        )
    with pytest.raises(SimulationIdempotencyError, match="SHA-256"):
        claim(store, db, StrategyScope(1), fingerprint="private scenario content")


def test_database_constraints_operation_state_and_resource_fk(db):
    base = dict(
        idempotency_key="key", request_fingerprint="a" * 64, actor_user_id=1,
        owner_user_id=1, organization_id=None, workspace_id=None,
        status="in_progress", claim_token="00000000-0000-4000-8000-000000000001",
        lease_expires_at=datetime.now(timezone.utc),
    )
    for changes in (
        {"operation": "simulation_rerun"},
        {"operation": SIMULATION_CREATE_OPERATION, "status": "failed"},
    ):
        with pytest.raises(IntegrityError):
            with db.begin_nested():
                db.execute(insert(simulation_create_idempotency_table), {**base, **changes})
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            db.execute(insert(simulation_create_idempotency_table), {
                **base, "operation": SIMULATION_CREATE_OPERATION,
                "status": "completed", "claim_token": None, "lease_expires_at": None,
                "simulation_resource_id": 99999,
            })


def test_storage_is_digest_only_private_and_capability_isolated():
    columns = set(simulation_create_idempotency_table.c.keys())
    assert columns == {
        "id", "idempotency_key", "operation", "request_fingerprint", "actor_user_id",
        "owner_user_id", "organization_id", "workspace_id", "status", "claim_token",
        "lease_expires_at", "simulation_resource_id", "created_at", "updated_at",
    }
    assert "strategy_resource_id" not in columns
    for forbidden in ("scenario", "strategy_text", "objective", "prompt", "provider", "error"):
        assert forbidden not in columns
    source = Path("app/simulation/idempotency.py").read_text(encoding="utf-8").casefold()
    for forbidden in (
        "modelprovider", "generate_structured", "fastapi", "requests", "httpx",
        "app.lab", "simulationstate", "simulation_history", "simulationorchestrator",
    ):
        assert forbidden not in source
