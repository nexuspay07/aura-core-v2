from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, event, insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

import app.db.schema  # noqa: F401 - register the complete metadata graph
from app.db.database import metadata
from app.db.organization_table import organization_table
from app.db.strategy_idempotency_table import strategy_create_idempotency_table
from app.db.strategy_resource_table import strategy_resource_table, strategy_revision_table
from app.db.user_table import user_table
from app.db.workspace_table import workspace_table
from app.strategy.contracts import ConfidenceLevel, StrategyInput, StrategyPhase, StrategyResult, StrategyScope, SuccessMeasure
from app.strategy.idempotency import (
    CLAIM_LEASE_DURATION,
    StrategyCreateClaimState,
    StrategyCreateOperation,
    StrategyCreateIdempotencyRepository,
    StrategyIdempotencyError,
    StrategyIdempotencyCompletionError,
    strategy_create_from_decision_fingerprint,
    strategy_create_request_fingerprint,
)
from app.intelligence_v2.model_provider import analysis_timeout_seconds
from app.strategy.persistence import StrategyRepository


def direct_input(scope=StrategyScope(1), **changes):
    values = {
        "scope": scope,
        "objective": "Retain customers",
        "chosen_direction": "Improve reliability",
        "constraints": (),
        "confidence": ConfidenceLevel.LOW,
        "confidence_rationale": ("No completed Decision evaluation.",),
    }
    values.update(changes)
    return StrategyInput(**values)


def result_for(source):
    return StrategyResult(
        scope=source.scope,
        objective=source.objective,
        chosen_direction=source.chosen_direction,
        approach="Stabilize dependencies before expanding.",
        phases=(StrategyPhase(1, "Stabilize", "Reduce reliability risk."),),
        success_measures=(SuccessMeasure("Reliability improves."),),
        change_conditions=("Reliability does not improve.",),
        confidence=source.confidence,
        confidence_rationale=source.confidence_rationale,
    )


@pytest.fixture
def database(tmp_path):
    path = tmp_path / "idempotency.db"
    engine = create_engine(f"sqlite:///{path}")
    event.listen(engine, "connect", lambda connection, _: connection.execute("PRAGMA foreign_keys=ON"))
    metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    db = factory()
    db.execute(insert(user_table), [
        {"id": 1, "email": "one@idempotency.test", "password_hash": "x"},
        {"id": 2, "email": "two@idempotency.test", "password_hash": "x"},
    ])
    db.execute(insert(organization_table), [
        {"id": 10, "name": "One", "slug": "one-idempotency", "owner_user_id": 1, "account_type": "business", "plan": "free", "subscription_status": "inactive", "is_active": True},
        {"id": 20, "name": "Two", "slug": "two-idempotency", "owner_user_id": 2, "account_type": "business", "plan": "free", "subscription_status": "inactive", "is_active": True},
    ])
    db.execute(insert(workspace_table), [
        {"id": 11, "organization_id": 10, "created_by_user_id": 1, "name": "One", "slug": "one-idempotency-workspace", "workspace_type": "business", "is_active": True},
        {"id": 12, "organization_id": 10, "created_by_user_id": 1, "name": "Other", "slug": "other-idempotency-workspace", "workspace_type": "business", "is_active": True},
        {"id": 21, "organization_id": 20, "created_by_user_id": 2, "name": "Two", "slug": "two-idempotency-workspace", "workspace_type": "business", "is_active": True},
    ])
    db.commit()
    yield factory, engine
    engine.dispose()


def test_fingerprint_is_deterministic_normalized_and_sensitive_to_effective_request():
    source = direct_input()
    first = strategy_create_request_fingerprint(title="  Reliability   plan ", strategy_input=source)
    assert first == strategy_create_request_fingerprint(title="Reliability plan", strategy_input=source)
    assert len(first) == 64
    assert first != strategy_create_request_fingerprint(title="Different", strategy_input=source)
    assert first != strategy_create_request_fingerprint(title="Reliability plan", strategy_input=direct_input(objective="Grow"))
    assert first != strategy_create_request_fingerprint(title="Reliability plan", strategy_input=direct_input(chosen_direction="Expand"))
    assert first != strategy_create_request_fingerprint(title="Reliability plan", strategy_input=direct_input(uncertainties=("Demand",)))
    assert first != strategy_create_request_fingerprint(title="Reliability plan", strategy_input=direct_input(StrategyScope(1, 10, 11)))


def test_first_active_duplicate_and_conflicting_claim_states(database):
    factory, _ = database
    db = factory(); repository = StrategyCreateIdempotencyRepository(); scope = StrategyScope(1)
    fingerprint = strategy_create_request_fingerprint(title="Plan", strategy_input=direct_input(scope))
    first = repository.claim(db, idempotency_key="opaque-key", request_fingerprint=fingerprint, actor_user_id=1, scope=scope)
    db.commit()
    same = repository.claim(db, idempotency_key="opaque-key", request_fingerprint=fingerprint, actor_user_id=1, scope=scope)
    conflict = repository.claim(db, idempotency_key="opaque-key", request_fingerprint="a" * 64, actor_user_id=1, scope=scope)
    assert first.state is StrategyCreateClaimState.CLAIMED and first.claim_token
    assert same.state is StrategyCreateClaimState.IN_PROGRESS
    assert conflict.state is StrategyCreateClaimState.CONFLICT
    db.close()


def test_same_key_is_isolated_by_actor_and_workspace(database):
    factory, _ = database
    db = factory(); repository = StrategyCreateIdempotencyRepository(); fingerprint = "b" * 64
    claims = [
        repository.claim(db, idempotency_key="shared", request_fingerprint=fingerprint, actor_user_id=1, scope=StrategyScope(1)),
        repository.claim(db, idempotency_key="shared", request_fingerprint=fingerprint, actor_user_id=2, scope=StrategyScope(2)),
        repository.claim(db, idempotency_key="shared", request_fingerprint=fingerprint, actor_user_id=1, scope=StrategyScope(1, 10, 11)),
        repository.claim(db, idempotency_key="shared", request_fingerprint=fingerprint, actor_user_id=1, scope=StrategyScope(1, 10, 12)),
    ]
    assert all(item.state is StrategyCreateClaimState.CLAIMED for item in claims)
    db.commit()
    assert db.execute(select(strategy_create_idempotency_table)).all().__len__() == 4
    db.close()


def test_database_uniqueness_prevents_two_personal_owners(database):
    factory, _ = database
    db = factory(); now = datetime.now(timezone.utc)
    values = dict(idempotency_key="duplicate", operation="strategy_create_direct", request_fingerprint="c" * 64,
                  actor_user_id=1, owner_user_id=1, organization_id=None, workspace_id=None,
                  status="in_progress", claim_token="00000000-0000-0000-0000-000000000001",
                  lease_expires_at=now + CLAIM_LEASE_DURATION)
    db.execute(insert(strategy_create_idempotency_table), values)
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            db.execute(insert(strategy_create_idempotency_table), {**values, "claim_token": "00000000-0000-0000-0000-000000000002"})
    db.close()


def test_expired_or_abandoned_claim_is_fenced_and_reclaimable(database):
    factory, _ = database
    db = factory(); repository = StrategyCreateIdempotencyRepository(); scope = StrategyScope(1)
    now = datetime(2026, 9, 24, tzinfo=timezone.utc); fingerprint = "d" * 64
    first = repository.claim(db, idempotency_key="lease", request_fingerprint=fingerprint, actor_user_id=1, scope=scope, now=now)
    db.commit()
    assert repository.claim(db, idempotency_key="lease", request_fingerprint=fingerprint, actor_user_id=1, scope=scope, now=now + timedelta(minutes=4)).state is StrategyCreateClaimState.IN_PROGRESS
    reclaimed = repository.claim(db, idempotency_key="lease", request_fingerprint=fingerprint, actor_user_id=1, scope=scope, now=now + CLAIM_LEASE_DURATION)
    assert reclaimed.state is StrategyCreateClaimState.CLAIMED and reclaimed.claim_token != first.claim_token
    assert repository.abandon_claim(db, idempotency_key="lease", actor_user_id=1, scope=scope, claim_token=reclaimed.claim_token, now=now + timedelta(minutes=6))
    db.commit()
    retried = repository.claim(db, idempotency_key="lease", request_fingerprint=fingerprint, actor_user_id=1, scope=scope, now=now + timedelta(minutes=6))
    assert retried.state is StrategyCreateClaimState.CLAIMED and retried.claim_token != reclaimed.claim_token
    db.close()


def test_five_minute_lease_has_fenced_renewal_for_long_generation(database, monkeypatch):
    factory, _ = database
    monkeypatch.setenv("AURA_AI_TIMEOUT_SECONDS", "999")
    assert CLAIM_LEASE_DURATION == timedelta(minutes=5)
    assert analysis_timeout_seconds() == int(CLAIM_LEASE_DURATION.total_seconds())
    db = factory(); repository = StrategyCreateIdempotencyRepository(); scope = StrategyScope(1)
    started = datetime(2026, 9, 24, tzinfo=timezone.utc)
    claim = repository.claim(db, idempotency_key="renew", request_fingerprint="5" * 64,
                             actor_user_id=1, scope=scope, now=started)
    db.commit()
    assert repository.renew_claim(db, idempotency_key="renew", actor_user_id=1, scope=scope,
                                  claim_token=claim.claim_token, now=started + timedelta(minutes=4))
    db.commit()
    assert repository.claim(db, idempotency_key="renew", request_fingerprint="5" * 64,
                            actor_user_id=1, scope=scope,
                            now=started + timedelta(minutes=6)).state is StrategyCreateClaimState.IN_PROGRESS
    assert not repository.renew_claim(db, idempotency_key="renew", actor_user_id=1, scope=scope,
                                      claim_token="stale", now=started + timedelta(minutes=6))
    db.close()


def test_only_one_reclaimer_becomes_owner(database):
    factory, _ = database
    repository = StrategyCreateIdempotencyRepository(); scope = StrategyScope(1); expired = datetime(2026, 1, 1, tzinfo=timezone.utc)
    first_db = factory(); claim = repository.claim(first_db, idempotency_key="race", request_fingerprint="e" * 64, actor_user_id=1, scope=scope, now=expired); first_db.commit(); first_db.close()
    one = factory(); winner = repository.claim(one, idempotency_key="race", request_fingerprint="e" * 64, actor_user_id=1, scope=scope, now=expired + timedelta(hours=1)); one.commit(); one.close()
    two = factory(); loser = repository.claim(two, idempotency_key="race", request_fingerprint="e" * 64, actor_user_id=1, scope=scope, now=expired + timedelta(hours=1)); two.close()
    assert claim.state is winner.state is StrategyCreateClaimState.CLAIMED
    assert loser.state is StrategyCreateClaimState.IN_PROGRESS


def test_expired_and_reclaimed_stale_claimant_cannot_complete(database):
    factory, _ = database
    db = factory(); repository = StrategyCreateIdempotencyRepository(); scope = StrategyScope(1); source = direct_input(scope)
    started = datetime(2026, 9, 24, tzinfo=timezone.utc)
    first = repository.claim(db, idempotency_key="stale", request_fingerprint="8" * 64,
                             actor_user_id=1, scope=scope, now=started)
    db.commit()
    with pytest.raises(StrategyIdempotencyCompletionError):
        repository.complete_with_strategy(
            db, idempotency_key="stale", request_fingerprint="8" * 64,
            actor_user_id=1, scope=scope, claim_token=first.claim_token,
            result=result_for(source), title="Plan", now=started + CLAIM_LEASE_DURATION,
        )
    db.rollback()
    current = repository.claim(db, idempotency_key="stale", request_fingerprint="8" * 64,
                               actor_user_id=1, scope=scope,
                               now=started + CLAIM_LEASE_DURATION)
    db.commit()
    assert current.state is StrategyCreateClaimState.CLAIMED
    with pytest.raises(StrategyIdempotencyCompletionError):
        repository.complete_with_strategy(
            db, idempotency_key="stale", request_fingerprint="8" * 64,
            actor_user_id=1, scope=scope, claim_token=first.claim_token,
            result=result_for(source), title="Plan",
            now=started + CLAIM_LEASE_DURATION + timedelta(seconds=1),
        )
    assert db.execute(select(strategy_resource_table)).all() == []
    db.rollback(); db.close()


def test_completion_atomically_links_one_strategy_and_replays(database):
    factory, _ = database
    db = factory(); repository = StrategyCreateIdempotencyRepository(); scope = StrategyScope(1); source = direct_input(scope)
    fingerprint = strategy_create_request_fingerprint(title="Plan", strategy_input=source)
    claim = repository.claim(db, idempotency_key="complete", request_fingerprint=fingerprint, actor_user_id=1, scope=scope); db.commit()
    persisted = repository.complete_with_strategy(db, idempotency_key="complete", request_fingerprint=fingerprint,
        actor_user_id=1, scope=scope, claim_token=claim.claim_token, result=result_for(source), title="Plan")
    db.commit()
    replay = repository.claim(db, idempotency_key="complete", request_fingerprint=fingerprint, actor_user_id=1, scope=scope)
    row = db.execute(select(strategy_create_idempotency_table)).mappings().one()
    assert replay.state is StrategyCreateClaimState.COMPLETED
    assert replay.strategy_resource_id == row["strategy_resource_id"]
    assert persisted.public_id and db.execute(select(strategy_resource_table)).all().__len__() == 1
    assert repository.claim(db, idempotency_key="complete", request_fingerprint="f" * 64, actor_user_id=1, scope=scope).state is StrategyCreateClaimState.CONFLICT
    db.close()


def test_completion_cannot_relink_or_use_wrong_claim(database):
    factory, _ = database
    db = factory(); repository = StrategyCreateIdempotencyRepository(); scope = StrategyScope(1); source = direct_input(scope); fingerprint = "1" * 64
    claim = repository.claim(db, idempotency_key="protected", request_fingerprint=fingerprint, actor_user_id=1, scope=scope); db.commit()
    for changes in ({"claim_token": "wrong"}, {"request_fingerprint": "2" * 64}, {"actor_user_id": 2}):
        values = dict(idempotency_key="protected", request_fingerprint=fingerprint, actor_user_id=1, scope=scope,
                      claim_token=claim.claim_token, result=result_for(source), title="Plan")
        values.update(changes)
        with pytest.raises(StrategyIdempotencyCompletionError):
            repository.complete_with_strategy(db, **values)
        assert db.execute(select(strategy_resource_table)).all() == []
    db.close()


def test_crash_before_outer_commit_rolls_back_strategy_and_completion(database):
    factory, _ = database
    db = factory(); repository = StrategyCreateIdempotencyRepository(); scope = StrategyScope(1); source = direct_input(scope); fingerprint = "3" * 64
    claim = repository.claim(db, idempotency_key="crash", request_fingerprint=fingerprint, actor_user_id=1, scope=scope); db.commit()
    repository.complete_with_strategy(db, idempotency_key="crash", request_fingerprint=fingerprint, actor_user_id=1,
        scope=scope, claim_token=claim.claim_token, result=result_for(source), title="Plan")
    db.rollback(); db.close()
    check = factory()
    assert check.execute(select(strategy_resource_table)).all() == []
    row = check.execute(select(strategy_create_idempotency_table)).mappings().one()
    assert row["status"] == "in_progress" and row["strategy_resource_id"] is None
    check.close()


def test_forced_completion_failure_rolls_back_resource_and_revision(database):
    factory, _ = database
    db = factory(); repository = StrategyCreateIdempotencyRepository(); scope = StrategyScope(1); source = direct_input(scope)
    claim = repository.claim(db, idempotency_key="completion-fails", request_fingerprint="6" * 64,
                             actor_user_id=1, scope=scope)
    db.commit()

    class StealClaimAfterPersistence(StrategyRepository):
        def create_strategy(self, db, **values):
            persisted = super().create_strategy(db, **values)
            db.execute(strategy_create_idempotency_table.update().values(claim_token="stolen"))
            return persisted

    with pytest.raises(StrategyIdempotencyCompletionError):
        repository.complete_with_strategy(
            db, idempotency_key="completion-fails", request_fingerprint="6" * 64,
            actor_user_id=1, scope=scope, claim_token=claim.claim_token,
            result=result_for(source), title="Plan", repository=StealClaimAfterPersistence(),
        )
    assert db.execute(select(strategy_resource_table)).all() == []
    assert db.execute(select(strategy_revision_table)).all() == []
    db.rollback(); db.close()


def test_strategy_persistence_failure_does_not_complete_claim(database):
    factory, _ = database
    db = factory(); repository = StrategyCreateIdempotencyRepository(); scope = StrategyScope(1); source = direct_input(scope)
    claim = repository.claim(db, idempotency_key="persistence-fails", request_fingerprint="7" * 64,
                             actor_user_id=1, scope=scope)
    db.commit()

    class FailedPersistence(StrategyRepository):
        def create_strategy(self, db, **values):
            raise RuntimeError("forced persistence failure")

    with pytest.raises(RuntimeError, match="forced persistence failure"):
        repository.complete_with_strategy(
            db, idempotency_key="persistence-fails", request_fingerprint="7" * 64,
            actor_user_id=1, scope=scope, claim_token=claim.claim_token,
            result=result_for(source), title="Plan", repository=FailedPersistence(),
        )
    row = db.execute(select(strategy_create_idempotency_table)).mappings().one()
    assert row["status"] == "in_progress" and row["strategy_resource_id"] is None
    assert db.execute(select(strategy_resource_table)).all() == []
    db.rollback(); db.close()


def test_state_constraint_and_privacy_safe_columns(database):
    factory, _ = database
    columns = set(strategy_create_idempotency_table.c.keys())
    assert columns == {"id", "idempotency_key", "operation", "request_fingerprint", "actor_user_id", "owner_user_id",
                       "organization_id", "workspace_id", "status", "claim_token", "lease_expires_at",
                       "strategy_resource_id", "created_at", "updated_at"}
    for forbidden in ("objective", "chosen_direction", "prompt", "provider", "jwt", "authorization", "error", "strategy_json"):
        assert forbidden not in columns
    db = factory(); now = datetime.now(timezone.utc)
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            db.execute(insert(strategy_create_idempotency_table), dict(
                idempotency_key="invalid", operation="strategy_create_direct", request_fingerprint="4" * 64,
                actor_user_id=1, owner_user_id=1, status="completed", claim_token=None,
                lease_expires_at=None, strategy_resource_id=None, created_at=now, updated_at=now,
            ))
    db.close()

def test_bounded_decision_operation_and_canonical_fingerprint(database):
    factory, _ = database
    db=factory(); repository=StrategyCreateIdempotencyRepository(); scope=StrategyScope(1); canonical=direct_input(scope, source_decision_id=9, source_reference="decision:public")
    digest=strategy_create_from_decision_fingerprint(title=" Plan ", strategy_input=canonical, personal_decision_public_id="decision-public", snapshot_public_id="snapshot-public", snapshot_version=2)
    assert digest == strategy_create_from_decision_fingerprint(title="Plan", strategy_input=canonical, personal_decision_public_id="decision-public", snapshot_public_id="snapshot-public", snapshot_version=2)
    claim=repository.claim(db,idempotency_key="decision-key",request_fingerprint=digest,actor_user_id=1,scope=scope,operation=StrategyCreateOperation.FROM_DECISION)
    assert claim.state is StrategyCreateClaimState.CLAIMED
    assert db.execute(select(strategy_create_idempotency_table.c.operation)).scalar_one()=="strategy_create_from_decision"
    with pytest.raises(StrategyIdempotencyError,match="Unsupported"):
        repository.claim(db,idempotency_key="bad",request_fingerprint="a"*64,actor_user_id=1,scope=scope,operation="arbitrary")
    db.close()
