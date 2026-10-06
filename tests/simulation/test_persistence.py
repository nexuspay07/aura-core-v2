from dataclasses import fields, replace
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

import app.db.schema  # noqa: F401
from app.db.database import metadata
from app.db.decision_execution_snapshot_table import decision_execution_snapshot_table
from app.db.organization_table import organization_table
from app.db.personal_decision_table import personal_decision_table
from app.db.simulation_resource_table import simulation_resource_table, simulation_run_table
from app.db.strategy_resource_table import strategy_resource_table, strategy_revision_table
from app.db.user_table import user_table
from app.db.workspace_table import workspace_table
from app.simulation import (
    FindingProvenance,
    ScenarioSeverity,
    ScenarioSource,
    SimulationFinding,
    SimulationLimitation,
    SimulationResultV1,
    SimulationScenario,
    StrategyStressResult,
    UserSimulationAssumption,
    build_simulation_input_from_strategy_revision,
)
from app.simulation.persistence import (
    DETERMINISM_MODE,
    SIMULATION_ENGINE_VERSION,
    PersistedSimulationResource,
    SimulationPersistenceError,
    SimulationPersistenceNotFoundError,
    hydrate_simulation_execution_input,
    hydrate_simulation_result,
    simulation_repository,
)
from app.simulation.serialization import simulation_to_dict
from app.strategy.contracts import (
    ConfidenceLevel,
    EvidenceReference,
    StrategyAssumption,
    StrategyConstraint,
    StrategyPhase,
    StrategyResult,
    StrategyRisk,
    StrategyScope,
    SuccessMeasure,
)
from app.strategy.persistence import serialize_strategy_result, strategy_repository


def strategy_result(scope, **changes):
    values = dict(
        scope=scope,
        objective="Retain key customers.",
        chosen_direction="Stabilize service before expanding.",
        approach="Strengthen reliability in ordered stages.",
        phases=(StrategyPhase(1, "Stabilize", "Reduce reliability risk."),),
        success_measures=(SuccessMeasure("Reliability remains stable.", "evidence-1"),),
        change_conditions=("Reliability declines.",),
        confidence=ConfidenceLevel.MODERATE,
        confidence_rationale=("Evidence is incomplete.",),
        constraints=(StrategyConstraint("continuity", "Maintain service continuity."),),
        assumptions=(StrategyAssumption("The team remains available.", "decision"),),
        risks=(StrategyRisk("Capacity may remain constrained.", "Gate expansion."),),
        uncertainties=("Demand timing remains uncertain.",),
        evidence_refs=(EvidenceReference("evidence-1", "Reliability review"),),
    )
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


def persisted_strategy(db, scope=StrategyScope(1), *, decision_snapshot=False):
    source_snapshot_id = None
    source_decision_id = None
    origin = "direct"
    if decision_snapshot:
        source_decision_id = 41
        origin = "decision_derived"
        db.execute(insert(personal_decision_table), {
            "id": 41, "public_id": "00000000-0000-4000-8000-000000000041",
            "user_id": 1, "organization_id": 10, "workspace_id": 11,
            "title": "Decision", "original_question": "What should we do?",
            "decision_type": "general", "analysis_snapshot_json": {},
            "recommendation": "Stabilize service",
        })
        inserted = db.execute(insert(decision_execution_snapshot_table).values(
            public_id="00000000-0000-4000-8000-000000000101",
            user_id=1, organization_id=10, workspace_id=11,
            snapshot_version=1, snapshot_schema_version=1, canonical_decision_json={},
        ))
        source_snapshot_id = inserted.inserted_primary_key[0]
        db.execute(update(personal_decision_table).where(
            personal_decision_table.c.id == 41,
        ).values(canonical_snapshot_id=source_snapshot_id))
    return strategy_repository.create_strategy(
        db,
        result=strategy_result(scope, source_decision_id=source_decision_id),
        title="Source strategy", created_by_user_id=scope.user_id,
        origin_type=origin, source_decision_snapshot_id=source_snapshot_id,
    )


def execution_for(strategy):
    return build_simulation_input_from_strategy_revision(
        strategy.result,
        strategy_schema_version=1,
        scenarios=(SimulationScenario(
            "adverse", "Adverse", "Demand rises before capacity improves.",
            ("Demand exceeds capacity.",), ScenarioSource.USER_SUPPLIED, ScenarioSeverity.HIGH,
        ),),
        user_assumptions=(UserSimulationAssumption("Staffing remains fixed.", "adverse"),),
    )


def accepted_result():
    finding = lambda text, provenance=FindingProvenance.MODEL_GENERATED: SimulationFinding(text, provenance, ("evidence-1",))
    return SimulationResultV1(
        scenario_results=(StrategyStressResult(
            "adverse",
            (finding("Capacity is under stress."),),
            (finding("Service effects may emerge."),),
            ScenarioSeverity.HIGH,
            constraint_conflicts=(finding("continuity", FindingProvenance.SOURCE),),
            phase_sensitivities=(finding("Stabilize", FindingProvenance.SOURCE),),
            change_condition_triggers=(finding("Reliability declines.", FindingProvenance.SOURCE),),
        ),),
        cross_scenario_comparison=(finding("The supplied scenario materially strains capacity.", FindingProvenance.DERIVED),),
        assumptions_used=(finding("Staffing remains fixed.", FindingProvenance.USER_SUPPLIED),),
        uncertainties=(finding("Recovery timing remains uncertain."),),
        limitations=(SimulationLimitation("not_calibrated", "This is scenario analysis, not calibrated forecasting."),),
        confidence=ConfidenceLevel.MODERATE,
        confidence_rationale=("The scenario is explicit but incomplete.",),
        evidence_refs=(EvidenceReference("evidence-1", "Reliability review"),),
    )


def create_resource(db, scope=StrategyScope(1), *, decision_snapshot=False):
    strategy = persisted_strategy(db, scope, decision_snapshot=decision_snapshot)
    execution = execution_for(strategy)
    resource = simulation_repository.create_resource(
        db, execution_input=execution, title="  Reliability stress test  ",
        scope=scope, created_by_user_id=scope.user_id,
    )
    return strategy, execution, resource


def test_create_personal_resource_with_exact_strategy_lineage(db):
    strategy, _, resource = create_resource(db)
    assert resource.title == "Reliability stress test"
    assert resource.scope == StrategyScope(1)
    assert resource.source_strategy_public_id == strategy.public_id
    assert resource.source_strategy_revision == 1
    assert resource.current_run_number == 0 and resource.lock_version == 1
    assert len(resource.public_id) == 36
    row = db.execute(select(simulation_resource_table)).mappings().one()
    assert row["owner_user_id"] == 1
    assert row["organization_id"] is row["workspace_id"] is None


def test_create_workspace_resource_and_exact_scope_isolation(db):
    scope = StrategyScope(1, 10, 11)
    _, _, resource = create_resource(db, scope)
    assert resource.scope == scope
    row = db.execute(select(simulation_resource_table)).mappings().one()
    assert row["owner_user_id"] is None
    assert (row["organization_id"], row["workspace_id"]) == (10, 11)
    assert simulation_repository.get_workspace_resource(
        db, public_id=resource.public_id, organization_id=10, workspace_id=11,
    ) == resource
    for organization_id, workspace_id in ((10, 12), (20, 11), (20, 21)):
        with pytest.raises(SimulationPersistenceNotFoundError):
            simulation_repository.get_workspace_resource(
                db, public_id=resource.public_id,
                organization_id=organization_id, workspace_id=workspace_id,
            )


def test_mixed_tenancy_and_duplicate_public_id_are_database_rejected(db):
    strategy, _, resource = create_resource(db)
    row = dict(db.execute(select(simulation_resource_table)).mappings().one())
    row.pop("id")
    row.update(owner_user_id=1, organization_id=10, workspace_id=11, public_id="00000000-0000-4000-8000-000000000099")
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            db.execute(insert(simulation_resource_table), row)
    row.update(owner_user_id=1, organization_id=None, workspace_id=None, public_id=resource.public_id)
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            db.execute(insert(simulation_resource_table), row)
    assert strategy.public_id == resource.source_strategy_public_id


def test_strategy_scope_mismatches_are_opaque_or_rejected(db):
    personal = persisted_strategy(db, StrategyScope(1))
    execution = execution_for(personal)
    for scope in (StrategyScope(2), StrategyScope(1, 10, 11)):
        with pytest.raises(SimulationPersistenceNotFoundError):
            simulation_repository.create_resource(
                db, execution_input=execution, title="Invalid",
                scope=scope, created_by_user_id=scope.user_id,
            )

    workspace = persisted_strategy(db, StrategyScope(1, 10, 11))
    workspace_execution = execution_for(workspace)
    for scope in (StrategyScope(1), StrategyScope(1, 10, 12), StrategyScope(2, 20, 21)):
        with pytest.raises(SimulationPersistenceNotFoundError):
            simulation_repository.create_resource(
                db, execution_input=workspace_execution, title="Invalid",
                scope=scope, created_by_user_id=scope.user_id,
            )


def test_revision_must_belong_to_strategy_and_revision_one_remains_pinned(db):
    strategy, execution, resource = create_resource(db)
    strategy_row = db.execute(select(strategy_resource_table).where(
        strategy_resource_table.c.public_id == strategy.public_id,
    )).mappings().one()
    db.execute(insert(strategy_revision_table).values(
        strategy_id=strategy_row["id"], revision_number=2,
        canonical_result_json=serialize_strategy_result(strategy_result(StrategyScope(1), objective="Revision two")),
        snapshot_schema_version=1, created_by_user_id=1, origin_type="direct",
    ))
    db.execute(update(strategy_resource_table).where(
        strategy_resource_table.c.id == strategy_row["id"],
    ).values(current_revision_number=2))
    fetched = simulation_repository.get_personal_resource(db, public_id=resource.public_id, owner_user_id=1)
    assert fetched.source_strategy_revision == 1
    invalid = replace(execution, provenance=replace(execution.provenance, strategy_revision=3))
    with pytest.raises(SimulationPersistenceError, match="does not belong"):
        simulation_repository.create_resource(
            db, execution_input=invalid, title="Invalid", scope=StrategyScope(1), created_by_user_id=1,
        )


def test_decision_snapshot_is_copied_exactly_and_null_is_allowed(db):
    _, _, direct = create_resource(db)
    assert direct.source_decision_snapshot_public_id is None
    db.rollback()
    _, _, derived = create_resource(db, StrategyScope(1, 10, 11), decision_snapshot=True)
    assert derived.source_decision_snapshot_public_id == "00000000-0000-4000-8000-000000000101"
    resource_row = db.execute(select(simulation_resource_table).where(
        simulation_resource_table.c.public_id == derived.public_id,
    )).mappings().one()
    revision_row = db.execute(select(strategy_revision_table).where(
        strategy_revision_table.c.id == resource_row["source_strategy_revision_id"],
    )).mappings().one()
    assert resource_row["source_decision_snapshot_id"] == revision_row["source_decision_snapshot_id"]


def test_mismatched_decision_snapshot_lineage_is_detected_on_hydration(db):
    _, _, resource = create_resource(db, StrategyScope(1, 10, 11), decision_snapshot=True)
    db.execute(update(simulation_resource_table).values(source_decision_snapshot_id=None))
    with pytest.raises(SimulationPersistenceError, match="does not match"):
        simulation_repository.get_workspace_resource(
            db, public_id=resource.public_id, organization_id=10, workspace_id=11,
        )


def test_append_immutable_runs_round_trip_and_preserve_run_one(db):
    _, execution, resource = create_resource(db)
    result = accepted_result()
    first = simulation_repository.append_run(
        db, resource_public_id=resource.public_id, scope=StrategyScope(1),
        execution_input=execution, result=result, created_by_user_id=1,
        provider_name="openai", model_name="gpt-test",
    )
    first_row_before = dict(db.execute(select(simulation_run_table).where(
        simulation_run_table.c.run_number == 1,
    )).mappings().one())
    second = simulation_repository.append_run(
        db, resource_public_id=resource.public_id, scope=StrategyScope(1),
        execution_input=execution, result=result, created_by_user_id=1,
    )
    first_row_after = dict(db.execute(select(simulation_run_table).where(
        simulation_run_table.c.run_number == 1,
    )).mappings().one())
    assert first.run_number == 1 and second.run_number == 2
    assert first.execution_input == execution and first.result == result
    assert first.engine_version == SIMULATION_ENGINE_VERSION
    assert first.determinism_mode == DETERMINISM_MODE
    assert (first.provider_name, first.model_name) == ("openai", "gpt-test")
    assert second.provider_name is second.model_name is None
    assert first_row_before == first_row_after
    assert simulation_repository.get_latest_run(
        db, resource_public_id=resource.public_id, scope=StrategyScope(1),
    ) == second


def test_snapshot_helpers_round_trip_and_reject_authority_injection(db):
    strategy = persisted_strategy(db)
    execution, result = execution_for(strategy), accepted_result()
    assert hydrate_simulation_execution_input(simulation_to_dict(execution)) == execution
    assert hydrate_simulation_result(simulation_to_dict(result), execution) == result
    injected = {**simulation_to_dict(execution), "owner_user_id": 999}
    with pytest.raises(SimulationPersistenceError, match="Malformed"):
        hydrate_simulation_execution_input(injected)


def test_run_number_uniqueness_and_no_content_update_api(db):
    _, execution, resource = create_resource(db)
    simulation_repository.append_run(
        db, resource_public_id=resource.public_id, scope=StrategyScope(1),
        execution_input=execution, result=accepted_result(), created_by_user_id=1,
    )
    row = db.execute(select(simulation_run_table)).mappings().one()
    duplicate = dict(row)
    duplicate.pop("id")
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            db.execute(insert(simulation_run_table), duplicate)
    method_names = set(dir(simulation_repository))
    assert not any(name.startswith("update_run") or "update_input" in name or "update_result" in name for name in method_names)


def test_provider_metadata_rejects_credential_or_prompt_shaped_values(db):
    _, execution, resource = create_resource(db)
    for metadata_value in ("api_key=secret", "provider prompt text", "secret@provider"):
        with pytest.raises(SimulationPersistenceError, match="provider_name"):
            simulation_repository.append_run(
                db, resource_public_id=resource.public_id, scope=StrategyScope(1),
                execution_input=execution, result=accepted_result(), created_by_user_id=1,
                provider_name=metadata_value,
            )


def test_personal_fetch_and_listing_are_tenant_safe(db):
    _, _, first = create_resource(db)
    _, _, second = create_resource(db)
    other_strategy = persisted_strategy(db, StrategyScope(2))
    other = simulation_repository.create_resource(
        db, execution_input=execution_for(other_strategy), title="Other",
        scope=StrategyScope(2), created_by_user_id=2,
    )
    assert [item.public_id for item in simulation_repository.list_personal_resources(db, owner_user_id=1)] == [second.public_id, first.public_id]
    assert [item.public_id for item in simulation_repository.list_personal_resources(db, owner_user_id=2)] == [other.public_id]
    with pytest.raises(SimulationPersistenceNotFoundError):
        simulation_repository.get_personal_resource(db, public_id=first.public_id, owner_user_id=2)


def test_workspace_listing_is_exact_and_archive_hides_from_lists(db):
    _, _, first = create_resource(db, StrategyScope(1, 10, 11))
    _, _, second = create_resource(db, StrategyScope(1, 10, 12))
    assert [item.public_id for item in simulation_repository.list_workspace_resources(
        db, organization_id=10, workspace_id=11,
    )] == [first.public_id]
    archived = simulation_repository.archive_workspace_resource(
        db, public_id=first.public_id, organization_id=10, workspace_id=11,
        expected_lock_version=1,
    )
    assert archived.archived_at is not None and archived.lock_version == 2
    assert simulation_repository.list_workspace_resources(db, organization_id=10, workspace_id=11) == []
    assert second.archived_at is None


def test_public_hydration_has_no_internal_numeric_identity_fields(db):
    _, execution, resource = create_resource(db)
    run = simulation_repository.append_run(
        db, resource_public_id=resource.public_id, scope=StrategyScope(1),
        execution_input=execution, result=accepted_result(), created_by_user_id=1,
    )
    forbidden = {"id", "strategy_id", "strategy_revision_id", "decision_snapshot_id", "simulation_resource_id"}
    assert {item.name for item in fields(PersistedSimulationResource)}.isdisjoint(forbidden)
    assert set(resource.__dict__).isdisjoint(forbidden)
    assert set(run.__dict__).isdisjoint(forbidden)


def test_repository_has_no_legacy_provider_http_or_orchestrator_coupling():
    source = Path("app/simulation/persistence.py").read_text(encoding="utf-8").casefold()
    for forbidden in (
        "app.lab", "simulationstate", "simulation_history", "fastapi", "openai",
        "generate_structured", "simulationorchestrator", "api_key", "credentials",
    ):
        assert forbidden not in source
