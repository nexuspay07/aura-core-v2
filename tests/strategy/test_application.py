from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, event, insert, select, update
from sqlalchemy.orm import sessionmaker

import app.db.schema  # noqa: F401 - register the complete metadata graph
from app.db.database import metadata
from app.db.organization_table import organization_table
from app.db.personal_decision_table import personal_decision_table
from app.db.strategy_resource_table import strategy_resource_table, strategy_revision_table
from app.db.user_table import user_table
from app.db.workspace_table import workspace_table
from app.strategy.application import (
    StrategyApplicationConflictError,
    StrategyApplicationNotFoundError,
    StrategyApplicationPersistenceError,
    StrategyApplicationService,
    StrategyApplicationValidationError,
)
from app.strategy.contracts import (
    ConfidenceLevel,
    StrategyInput,
    StrategyPhase,
    StrategyResult,
    StrategyScope,
    SuccessMeasure,
)
from app.strategy.orchestrator import StrategyGenerationError
from app.strategy.persistence import (
    PersistedStrategy,
    StrategyPersistenceError,
    StrategyRepository,
)


def strategy_input(scope=StrategyScope(1), **changes):
    values = {
        "scope": scope,
        "objective": "Retain key customers",
        "chosen_direction": "Improve reliability",
        "change_conditions": ("Reliability does not improve.",),
        "confidence": ConfidenceLevel.LOW,
        "confidence_rationale": ("Direct input has no completed Decision evaluation.",),
    }
    values.update(changes)
    return StrategyInput(**values)


def generated_result(source: StrategyInput, **changes):
    values = {
        "scope": source.scope,
        "objective": source.objective,
        "chosen_direction": source.chosen_direction,
        "approach": "Stabilize dependencies before expanding.",
        "phases": (StrategyPhase(1, "Stabilize", "Reduce reliability risk."),),
        "success_measures": (SuccessMeasure("Reliability improves."),),
        "change_conditions": source.change_conditions,
        "confidence": source.confidence,
        "confidence_rationale": source.confidence_rationale,
        "source_decision_id": source.source_decision_id,
        "source_reference": source.source_reference,
    }
    values.update(changes)
    return StrategyResult(**values)


class Capability:
    def __init__(self, *, result=None, error=None, before_return=None):
        self.result = result
        self.error = error
        self.before_return = before_return
        self.calls = 0

    def generate(self, source):
        self.calls += 1
        if self.before_return:
            self.before_return()
        if self.error:
            raise self.error
        return self.result or generated_result(source)


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
        {"id": 10, "name": "One", "slug": "one-app", "owner_user_id": 1, "account_type": "business", "plan": "free", "subscription_status": "inactive", "is_active": True},
        {"id": 20, "name": "Two", "slug": "two-app", "owner_user_id": 2, "account_type": "business", "plan": "free", "subscription_status": "inactive", "is_active": True},
    ])
    session.execute(insert(workspace_table), [
        {"id": 11, "organization_id": 10, "created_by_user_id": 1, "name": "One", "slug": "one-app-workspace", "workspace_type": "business", "is_active": True},
        {"id": 12, "organization_id": 10, "created_by_user_id": 1, "name": "Other", "slug": "other-app-workspace", "workspace_type": "business", "is_active": True},
        {"id": 21, "organization_id": 20, "created_by_user_id": 2, "name": "Two", "slug": "two-app-workspace", "workspace_type": "business", "is_active": True},
    ])
    session.execute(insert(personal_decision_table), {
        "id": 41,
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


def service(capability=None, repository=None):
    return StrategyApplicationService(capability or Capability(), repository or StrategyRepository())


def test_generate_then_persist_direct_has_one_call_and_no_open_model_transaction(db):
    capability = Capability(before_return=lambda: (
        db.execute(select(strategy_resource_table)).all() == []
        or pytest.fail("resource existed during generation")
    ))
    persisted = service(capability).generate_and_persist_direct_strategy(
        db,
        strategy_input=strategy_input(),
        title="  Reliability   strategy  ",
        created_by_user_id=1,
    )
    assert isinstance(persisted, PersistedStrategy)
    assert capability.calls == 1
    assert persisted.title == "Reliability strategy" and len(persisted.public_id) == 36
    assert persisted.scope == StrategyScope(1)
    assert persisted.current_revision_number == persisted.lock_version == 1
    assert persisted.origin_type == "direct" and persisted.source_decision_id is None
    assert db.execute(select(strategy_revision_table)).mappings().one()["revision_number"] == 1


def test_workspace_ownership_is_derived_only_from_canonical_scope(db):
    persisted = service().generate_and_persist_direct_strategy(
        db,
        strategy_input=strategy_input(StrategyScope(1, 10, 11)),
        title="Workspace strategy",
        created_by_user_id=1,
    )
    row = db.execute(select(strategy_resource_table)).mappings().one()
    assert persisted.scope == StrategyScope(1, 10, 11)
    assert row["owner_user_id"] is None and (row["organization_id"], row["workspace_id"]) == (10, 11)


def test_generation_failure_creates_nothing_and_retains_generation_error(db):
    capability = Capability(error=StrategyGenerationError("private provider detail"))
    with pytest.raises(StrategyGenerationError, match="private provider detail"):
        service(capability).generate_and_persist_direct_strategy(
            db, strategy_input=strategy_input(), title="Valid", created_by_user_id=1
        )
    assert capability.calls == 1
    assert db.execute(select(strategy_resource_table)).all() == []


def test_persistence_failure_is_controlled_and_not_false_success(db):
    class FailingRepository(StrategyRepository):
        def create_strategy(self, db, **values):
            raise StrategyPersistenceError("private database detail")

    with pytest.raises(StrategyApplicationPersistenceError) as captured:
        service(repository=FailingRepository()).generate_and_persist_direct_strategy(
            db, strategy_input=strategy_input(), title="Valid", created_by_user_id=1
        )
    assert "private" not in str(captured.value)
    assert db.execute(select(strategy_resource_table)).all() == []


def test_persist_existing_uses_zero_provider_calls_and_validates_provenance(db):
    capability = Capability()
    application = service(capability)
    result = generated_result(strategy_input())
    persisted = application.persist_existing_strategy(
        db, result=result, title="Approved", created_by_user_id=1, origin_type="direct"
    )
    assert capability.calls == 0 and persisted.result.version == 1
    with pytest.raises(StrategyApplicationValidationError, match="source Decision"):
        application.persist_existing_strategy(
            db,
            result=generated_result(strategy_input(), source_decision_id=9),
            title="Invalid",
            created_by_user_id=1,
            origin_type="direct",
        )
    with pytest.raises(StrategyApplicationValidationError, match="identity or version"):
        application.persist_existing_strategy(
            db,
            result=generated_result(strategy_input(), strategy_id="selected"),
            title="Invalid",
            created_by_user_id=1,
            origin_type="direct",
        )


def test_authorized_decision_derived_provenance_is_preserved_without_provider(db):
    capability = Capability()
    persisted = service(capability).persist_existing_strategy(
        db,
        result=generated_result(
            strategy_input(StrategyScope(1, 10, 11)),
            source_decision_id=41,
            source_reference="personal-decision:41",
        ),
        title="Decision-derived",
        created_by_user_id=1,
        origin_type="decision_derived",
    )
    assert capability.calls == 0
    assert persisted.origin_type == "decision_derived"
    assert persisted.source_decision_id == persisted.result.source_decision_id == 41
    assert persisted.result.source_reference == "personal-decision:41"


@pytest.mark.parametrize("title", [None, "", "   ", "x" * 256])
def test_invalid_title_is_rejected_before_provider_call(db, title):
    capability = Capability()
    with pytest.raises(StrategyApplicationValidationError, match="title"):
        service(capability).generate_and_persist_direct_strategy(
            db, strategy_input=strategy_input(), title=title, created_by_user_id=1
        )
    assert capability.calls == 0


def test_invalid_input_or_scope_is_rejected_before_provider_call(db):
    capability = Capability()
    with pytest.raises(StrategyApplicationValidationError):
        service(capability).generate_and_persist_direct_strategy(
            db,
            strategy_input=strategy_input(StrategyScope(1, 10, None)),
            title="Invalid",
            created_by_user_id=1,
        )
    assert capability.calls == 0


def test_personal_and_workspace_current_reads_are_tenant_safe(db):
    application = service()
    personal = application.persist_existing_strategy(
        db, result=generated_result(strategy_input()), title="Personal", created_by_user_id=1, origin_type="direct"
    )
    workspace = application.persist_existing_strategy(
        db,
        result=generated_result(strategy_input(StrategyScope(1, 10, 11))),
        title="Workspace",
        created_by_user_id=1,
        origin_type="direct",
    )
    assert application.get_current_personal_strategy(db, public_id=personal.public_id, scope=StrategyScope(1)) == personal
    assert application.get_current_workspace_strategy(db, public_id=workspace.public_id, scope=StrategyScope(1, 10, 11)) == workspace
    with pytest.raises(StrategyApplicationNotFoundError):
        application.get_current_personal_strategy(db, public_id=personal.public_id, scope=StrategyScope(2))
    for scope in (StrategyScope(1, 20, 21), StrategyScope(1, 10, 12)):
        with pytest.raises(StrategyApplicationNotFoundError):
            application.get_current_workspace_strategy(db, public_id=workspace.public_id, scope=scope)


def test_lists_are_bounded_ordered_hydrated_and_exclude_other_tenants_and_archived(db):
    application = service()
    first = application.persist_existing_strategy(
        db, result=generated_result(strategy_input()), title="First", created_by_user_id=1, origin_type="direct"
    )
    second = application.persist_existing_strategy(
        db, result=generated_result(strategy_input()), title="Second", created_by_user_id=1, origin_type="direct"
    )
    application.persist_existing_strategy(
        db, result=generated_result(strategy_input(StrategyScope(2))), title="Other", created_by_user_id=2, origin_type="direct"
    )
    earlier = datetime.now(timezone.utc) - timedelta(days=1)
    db.execute(update(strategy_resource_table).where(strategy_resource_table.c.public_id == first.public_id).values(updated_at=earlier))

    listed = application.list_personal_strategies(db, scope=StrategyScope(1), limit=2)
    assert [item.public_id for item in listed] == [second.public_id, first.public_id]
    assert all(isinstance(item, PersistedStrategy) and isinstance(item.result, StrategyResult) for item in listed)
    application.archive_strategy(
        db, public_id=second.public_id, scope=StrategyScope(1), expected_lock_version=1
    )
    assert [item.public_id for item in application.list_personal_strategies(db, scope=StrategyScope(1))] == [first.public_id]
    with pytest.raises(StrategyApplicationPersistenceError):
        application.list_personal_strategies(db, scope=StrategyScope(1), limit=101)


def test_workspace_list_uses_exact_scope(db):
    application = service()
    target = application.persist_existing_strategy(
        db,
        result=generated_result(strategy_input(StrategyScope(1, 10, 11))),
        title="Target",
        created_by_user_id=1,
        origin_type="direct",
    )
    application.persist_existing_strategy(
        db,
        result=generated_result(strategy_input(StrategyScope(1, 10, 12))),
        title="Other workspace",
        created_by_user_id=1,
        origin_type="direct",
    )
    listed = application.list_workspace_strategies(db, scope=StrategyScope(1, 10, 11))
    assert [item.public_id for item in listed] == [target.public_id]


def test_archive_is_idempotent_and_preserves_revision_content(db):
    application = service()
    persisted = application.persist_existing_strategy(
        db, result=generated_result(strategy_input()), title="Archive", created_by_user_id=1, origin_type="direct"
    )
    before = db.execute(select(strategy_revision_table)).mappings().one()
    archived = application.archive_strategy(
        db, public_id=persisted.public_id, scope=StrategyScope(1), expected_lock_version=1
    )
    repeated = application.archive_strategy(
        db, public_id=persisted.public_id, scope=StrategyScope(1), expected_lock_version=1
    )
    after = db.execute(select(strategy_revision_table)).mappings().one()
    assert archived.archived_at is not None and archived.lock_version == 2
    assert repeated.lock_version == 2 and repeated.archived_at is not None
    assert archived.updated_at >= persisted.updated_at
    assert archived.current_revision_number == 1
    assert before["canonical_result_json"] == after["canonical_result_json"]
    assert db.execute(select(strategy_revision_table)).mappings().all() == [after]


def test_workspace_archive_is_scoped_and_stale_lock_conflicts(db):
    application = service()
    persisted = application.persist_existing_strategy(
        db,
        result=generated_result(strategy_input(StrategyScope(1, 10, 11))),
        title="Workspace archive",
        created_by_user_id=1,
        origin_type="direct",
    )
    with pytest.raises(StrategyApplicationNotFoundError):
        application.archive_strategy(
            db, public_id=persisted.public_id, scope=StrategyScope(2, 20, 21), expected_lock_version=1
        )
    db.execute(update(strategy_resource_table).where(
        strategy_resource_table.c.public_id == persisted.public_id
    ).values(lock_version=2))
    with pytest.raises(StrategyApplicationConflictError):
        application.archive_strategy(
            db, public_id=persisted.public_id, scope=StrategyScope(1, 10, 11), expected_lock_version=1
        )


def test_application_boundary_has_no_http_or_cross_product_dependencies():
    source = __import__("pathlib").Path("app/strategy/application.py").read_text(encoding="utf-8").lower()
    for forbidden in (
        "fastapi", "jwt", "bearer", "marketplace", "simulation", "planning",
        "learning", "billing", "strategyrequest", "strategypresentation",
    ):
        assert forbidden not in source
