from dataclasses import replace

import pytest
from sqlalchemy import create_engine, event, insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

import app.db.schema  # noqa: F401 - register the complete metadata graph
from app.db.database import metadata
from app.db.organization_table import organization_table
from app.db.personal_decision_table import personal_decision_table
from app.db.strategy_resource_table import strategy_resource_table, strategy_revision_table
from app.db.user_table import user_table
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
from app.strategy.persistence import (
    SNAPSHOT_SCHEMA_VERSION,
    StrategyPersistenceError,
    StrategyPersistenceNotFoundError,
    hydrate_strategy_result,
    serialize_strategy_result,
    strategy_repository,
)


def canonical_result(scope=StrategyScope(1), **changes):
    values = {
        "scope": scope,
        "objective": "Retain key customers",
        "chosen_direction": "Improve service reliability",
        "approach": "Stabilize dependencies before expanding.",
        "phases": (StrategyPhase(1, "Stabilize", "Reduce risk.", ("Reliability",), "Review stability."),),
        "success_measures": (SuccessMeasure("Reliability improves.", "evidence-1"),),
        "change_conditions": ("Reliability does not improve.",),
        "confidence": ConfidenceLevel.LOW,
        "confidence_rationale": ("Direct input has no completed Decision evaluation.",),
        "source_reference": "authorized-source",
        "constraints": (StrategyConstraint("constraint-1", "Stay within budget."),),
        "assumptions": (StrategyAssumption("The vendor remains available.", "user_provided"),),
        "resources": (StrategyResource("Team", "Existing delivery team"),),
        "risks": (StrategyRisk("Delivery may slip.", "Use staged reviews."),),
        "alternatives": (StrategyAlternative("Delay", "Wait for more evidence."),),
        "uncertainties": ("Demand remains uncertain.",),
        "evidence_refs": (EvidenceReference("evidence-1", "Reliability review"),),
        "time_horizon": "Next planning horizon",
    }
    values.update(changes)
    return StrategyResult(**values)


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    event.listen(engine, "connect", lambda connection, _: connection.execute("PRAGMA foreign_keys=ON"))
    metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.execute(insert(user_table), [
        {"id": 1, "email": "one@test", "password_hash": "x"},
        {"id": 2, "email": "two@test", "password_hash": "x"},
        {"id": 3, "email": "creator@test", "password_hash": "x"},
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
    session.execute(insert(personal_decision_table), {
        "id": 41,
        "public_id": "00000000-0000-4000-8000-000000000041",
        "user_id": 1,
        "organization_id": 10,
        "workspace_id": 11,
        "title": "Decision",
        "original_question": "What should we do?",
        "decision_type": "general",
        "analysis_snapshot_json": {},
        "recommendation": "Improve reliability",
    })
    session.commit()
    yield session
    session.close()
    engine.dispose()


def test_snapshot_round_trip_is_lossless_and_scope_is_authoritative():
    original = canonical_result(StrategyScope(99, 98, 97), strategy_id="old", version=9, source_decision_id=41)
    snapshot = serialize_strategy_result(original)
    assert {"scope", "strategy_id", "version", "source_decision_id"}.isdisjoint(snapshot)
    assert "provider" not in repr(snapshot).lower() and "prompt" not in repr(snapshot).lower()

    hydrated = hydrate_strategy_result(
        snapshot,
        scope=StrategyScope(1, 10, 11),
        public_id="00000000-0000-0000-0000-000000000001",
        revision_number=1,
        source_decision_id=41,
        snapshot_schema_version=SNAPSHOT_SCHEMA_VERSION,
    )
    assert hydrated == replace(
        original,
        scope=StrategyScope(1, 10, 11),
        strategy_id="00000000-0000-0000-0000-000000000001",
        version=1,
    )


def test_malformed_or_authority_injecting_snapshot_is_rejected():
    snapshot = serialize_strategy_result(canonical_result())
    with pytest.raises(StrategyPersistenceError, match="Malformed"):
        hydrate_strategy_result(
            {**snapshot, "scope": {"user_id": 999}},
            scope=StrategyScope(1),
            public_id="id",
            revision_number=1,
            source_decision_id=None,
            snapshot_schema_version=1,
        )
    with pytest.raises(StrategyPersistenceError, match="Unsupported"):
        hydrate_strategy_result(snapshot, scope=StrategyScope(1), public_id="id", revision_number=1, source_decision_id=None, snapshot_schema_version=2)


def test_personal_create_and_tenant_safe_read_preserve_creator_separately(db):
    persisted = strategy_repository.create_strategy(
        db,
        result=canonical_result(StrategyScope(1)),
        title="  Reliability strategy  ",
        created_by_user_id=3,
        origin_type="direct",
    )
    assert persisted.title == "Reliability strategy"
    assert persisted.created_by_user_id == 3 and persisted.scope.user_id == 1
    assert persisted.current_revision_number == persisted.lock_version == persisted.result.version == 1
    assert len(persisted.public_id) == 36 and persisted.result.strategy_id == persisted.public_id
    assert persisted.source_decision_id is None and persisted.origin_type == "direct"
    assert strategy_repository.get_personal_strategy_by_public_id(
        db, public_id=persisted.public_id, owner_user_id=1
    ) == persisted
    with pytest.raises(StrategyPersistenceNotFoundError):
        strategy_repository.get_personal_strategy_by_public_id(db, public_id=persisted.public_id, owner_user_id=2)

    resource = db.execute(select(strategy_resource_table)).mappings().one()
    revision = db.execute(select(strategy_revision_table)).mappings().one()
    assert resource["owner_user_id"] == 1 and resource["organization_id"] is None and resource["workspace_id"] is None
    assert revision["revision_number"] == 1 and revision["snapshot_schema_version"] == 1


def test_workspace_create_checks_organization_and_scopes_every_read(db):
    persisted = strategy_repository.create_strategy(
        db,
        result=canonical_result(StrategyScope(1, 10, 11)),
        title="Workspace strategy",
        created_by_user_id=1,
        origin_type="direct",
    )
    assert persisted.scope == StrategyScope(1, 10, 11)
    assert strategy_repository.get_workspace_strategy_by_public_id(
        db, public_id=persisted.public_id, organization_id=10, workspace_id=11
    ) == persisted
    for organization_id, workspace_id in ((20, 11), (10, 12), (20, 21)):
        with pytest.raises(StrategyPersistenceNotFoundError):
            strategy_repository.get_workspace_strategy_by_public_id(
                db,
                public_id=persisted.public_id,
                organization_id=organization_id,
                workspace_id=workspace_id,
            )
    with pytest.raises(StrategyPersistenceError, match="does not belong"):
        strategy_repository.create_strategy(
            db,
            result=canonical_result(StrategyScope(1, 20, 11)),
            title="Invalid",
            created_by_user_id=1,
            origin_type="direct",
        )


def test_database_rejects_mixed_tenancy_shape(db):
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            db.execute(strategy_resource_table.insert().values(
                public_id="00000000-0000-0000-0000-000000000099",
                title="Invalid mixed scope",
                created_by_user_id=1,
                owner_user_id=1,
                organization_id=10,
                workspace_id=11,
                current_revision_number=1,
                lock_version=1,
            ))


@pytest.mark.parametrize("title", ["", "   ", "x" * 256])
def test_title_is_required_and_bounded(db, title):
    with pytest.raises(StrategyPersistenceError, match="title"):
        strategy_repository.create_strategy(
            db, result=canonical_result(), title=title, created_by_user_id=1, origin_type="direct"
        )


def test_decision_provenance_is_authorized_and_delete_sets_null(db):
    source = canonical_result(StrategyScope(1, 10, 11), source_decision_id=41)
    persisted = strategy_repository.create_strategy(
        db, result=source, title="Derived", created_by_user_id=1, origin_type="decision_derived"
    )
    db.execute(personal_decision_table.delete().where(personal_decision_table.c.id == 41))
    db.flush()
    refreshed = strategy_repository.get_workspace_strategy_by_public_id(
        db, public_id=persisted.public_id, organization_id=10, workspace_id=11
    )
    assert refreshed.origin_type == "decision_derived" and refreshed.source_decision_id is None


def test_direct_source_and_unauthorized_decision_are_rejected(db):
    source = canonical_result(StrategyScope(1, 10, 11), source_decision_id=41)
    with pytest.raises(StrategyPersistenceError, match="Direct"):
        strategy_repository.create_strategy(
            db, result=source, title="Direct", created_by_user_id=1, origin_type="direct"
        )
    with pytest.raises(StrategyPersistenceError, match="not authorized"):
        strategy_repository.create_strategy(
            db, result=source, title="Derived", created_by_user_id=2, origin_type="decision_derived"
        )


def test_revision_failure_rolls_back_resource_insert(db):
    engine = db.get_bind()

    def reject_revision(_connection, _cursor, statement, _parameters, _context, _executemany):
        if statement.lstrip().upper().startswith("INSERT INTO STRATEGY_REVISIONS"):
            raise RuntimeError("revision rejected")

    event.listen(engine, "before_cursor_execute", reject_revision)
    try:
        with pytest.raises(RuntimeError, match="revision rejected"):
            strategy_repository.create_strategy(
                db, result=canonical_result(), title="Atomic", created_by_user_id=1, origin_type="direct"
            )
    finally:
        event.remove(engine, "before_cursor_execute", reject_revision)
    assert db.execute(select(strategy_resource_table)).all() == []


def test_repository_exposes_no_revision_content_update_operation():
    assert not any("update_revision" in name for name in dir(strategy_repository))
