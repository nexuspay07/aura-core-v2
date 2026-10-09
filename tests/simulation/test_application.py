from dataclasses import fields
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import insert, select, update

from app.db.simulation_idempotency_table import simulation_create_idempotency_table
from app.db.simulation_resource_table import simulation_resource_table, simulation_run_table
from app.db.strategy_resource_table import strategy_resource_table, strategy_revision_table
from app.simulation.application import (
    CreateStrategyStressTestCommand,
    SimulationApplicationConflictError,
    SimulationApplicationGenerationError,
    SimulationApplicationInProgressError,
    SimulationApplicationInternalError,
    SimulationApplicationNotFoundError,
    SimulationApplicationPersistenceError,
    SimulationApplicationService,
    SimulationApplicationValidationError,
    StrategyStressTestApplicationResult,
    simulation_generation_lease_duration,
)
from app.simulation.contracts import FindingProvenance, ScenarioSeverity, ScenarioSource, SimulationScenario, UserSimulationAssumption
from app.simulation.idempotency import SimulationCreateIdempotencyStore
from app.simulation.persistence import SIMULATION_ENGINE_VERSION, SimulationPersistenceError, SimulationRepository
from app.simulation.orchestrator import SimulationOrchestrator
from app.strategy.contracts import StrategyScope
from app.strategy.persistence import serialize_strategy_result
from tests.simulation.test_persistence import accepted_result, db, persisted_strategy, strategy_result  # noqa: F401
from tests.simulation.test_orchestrator import RecordingProvider, valid_output


SCENARIO = SimulationScenario(
    "adverse", "Adverse", "Demand rises before capacity improves.",
    ("Demand exceeds capacity.",), ScenarioSource.USER_SUPPLIED, ScenarioSeverity.HIGH,
)
ASSUMPTION = UserSimulationAssumption("Staffing remains fixed.", "adverse")


def command(strategy, *, key="key", scenarios=(SCENARIO,), assumptions=(ASSUMPTION,), title="Reliability stress test"):
    return CreateStrategyStressTestCommand(strategy.public_id, scenarios, assumptions, title, key)


class Provider:
    provider_name = "recording"
    model_name = "offline"


class Orchestrator:
    def __init__(self, *, error=None, before_return=None):
        self.provider = Provider()
        self.error = error
        self.before_return = before_return
        self.calls = []

    def run(self, execution):
        self.calls.append(execution)
        if self.before_return:
            self.before_return()
        if self.error:
            raise self.error
        return accepted_result()


def service(orchestrator=None, repository=None):
    return SimulationApplicationService(
        orchestrator=orchestrator or Orchestrator(),
        simulation_repository=repository,
    )


@pytest.mark.parametrize("scope,decision", [(StrategyScope(1), False), (StrategyScope(1, 10, 11), True)])
def test_successful_personal_and_workspace_creation_preserves_safe_lineage(db, scope, decision):
    strategy = persisted_strategy(db, scope, decision_snapshot=decision)
    runner = Orchestrator()
    result = service(runner).create_strategy_stress_test(
        db, command=command(strategy), actor_user_id=1, scope=scope,
    )
    assert isinstance(result, StrategyStressTestApplicationResult)
    assert len(result.simulation_public_id) == 36
    assert result.source_strategy_public_id == strategy.public_id
    assert result.source_strategy_revision == 1
    assert result.source_decision_snapshot_public_id == (
        "00000000-0000-4000-8000-000000000101" if decision else None
    )
    assert result.run_number == 1 and runner.calls == [runner.calls[0]]
    assert runner.calls[0].simulation_input.scenarios == (SCENARIO,)
    assert runner.calls[0].simulation_input.user_assumptions == (ASSUMPTION,)
    assert runner.calls[0].simulation_input.user_assumptions[0].provenance is FindingProvenance.USER_SUPPLIED
    row = db.execute(select(simulation_run_table)).mappings().one()
    assert row["engine_version"] == SIMULATION_ENGINE_VERSION
    assert (row["provider_name"], row["model_name"]) == ("recording", "offline")
    assert set(item.name for item in fields(result)).isdisjoint({
        "id", "strategy_id", "strategy_revision_id", "owner_user_id",
        "organization_id", "workspace_id", "claim_token", "lock_version",
    })


def test_completed_retry_after_strategy_change_replays_without_provider_and_new_key_pins_new_revision(db):
    strategy = persisted_strategy(db)
    runner = Orchestrator()
    application = service(runner)
    first = application.create_strategy_stress_test(db, command=command(strategy), actor_user_id=1, scope=StrategyScope(1))
    strategy_row = db.execute(select(strategy_resource_table).where(strategy_resource_table.c.public_id == strategy.public_id)).mappings().one()
    db.execute(insert(strategy_revision_table).values(
        strategy_id=strategy_row["id"], revision_number=2,
        canonical_result_json=serialize_strategy_result(strategy_result(StrategyScope(1), objective="Revision two")),
        snapshot_schema_version=1, created_by_user_id=1, origin_type="direct",
    ))
    db.execute(update(strategy_resource_table).where(strategy_resource_table.c.id == strategy_row["id"]).values(current_revision_number=2))
    db.commit()
    replay = application.create_strategy_stress_test(db, command=command(strategy), actor_user_id=1, scope=StrategyScope(1))
    second = application.create_strategy_stress_test(db, command=command(strategy, key="key-2"), actor_user_id=1, scope=StrategyScope(1))
    assert replay.simulation_public_id == first.simulation_public_id
    assert replay.source_strategy_revision == 1
    assert len(runner.calls) == 2
    assert second.simulation_public_id != first.simulation_public_id
    assert second.source_strategy_revision == 2
    assert len(db.execute(select(simulation_resource_table)).all()) == 2
    assert len(db.execute(select(simulation_run_table)).all()) == 2


def test_revision_is_pinned_before_provider_even_when_current_revision_changes(db):
    scope = StrategyScope(1, 10, 11)
    strategy = persisted_strategy(db, scope, decision_snapshot=True)
    strategy_row = db.execute(select(strategy_resource_table).where(strategy_resource_table.c.public_id == strategy.public_id)).mappings().one()
    revision_one = db.execute(select(strategy_revision_table).where(
        strategy_revision_table.c.strategy_id == strategy_row["id"],
        strategy_revision_table.c.revision_number == 1,
    )).mappings().one()
    def advance():
        db.execute(insert(strategy_revision_table).values(
            strategy_id=strategy_row["id"], revision_number=2,
            canonical_result_json=serialize_strategy_result(strategy_result(scope, objective="Revision two", source_decision_id=41)),
            snapshot_schema_version=1, created_by_user_id=1, origin_type="decision_derived",
            source_decision_id=41, source_decision_snapshot_id=None,
        ))
        db.execute(update(strategy_resource_table).where(strategy_resource_table.c.id == strategy_row["id"]).values(current_revision_number=2))
    result = service(Orchestrator(before_return=advance)).create_strategy_stress_test(
        db, command=command(strategy), actor_user_id=1, scope=scope,
    )
    run = db.execute(select(simulation_run_table)).mappings().one()
    assert result.source_strategy_revision == 1
    assert result.source_decision_snapshot_public_id == "00000000-0000-4000-8000-000000000101"
    resource = db.execute(select(simulation_resource_table)).mappings().one()
    assert resource["source_decision_snapshot_id"] == revision_one["source_decision_snapshot_id"]
    assert run["canonical_execution_input_json"]["provenance"]["strategy_revision"] == 1


@pytest.mark.parametrize("scope", [StrategyScope(2), StrategyScope(1, 10, 11), StrategyScope(1, 10, 12), StrategyScope(2, 20, 21)])
def test_inaccessible_strategy_is_opaque_and_never_calls_provider(db, scope):
    strategy = persisted_strategy(db, StrategyScope(1))
    runner = Orchestrator()
    with pytest.raises(SimulationApplicationNotFoundError, match="Strategy not found"):
        service(runner).create_strategy_stress_test(db, command=command(strategy), actor_user_id=scope.user_id, scope=scope)
    assert runner.calls == []
    assert db.execute(select(simulation_resource_table)).all() == []


def test_invalid_scenario_and_assumption_are_rejected_before_claim_or_provider(db):
    strategy = persisted_strategy(db)
    runner = Orchestrator()
    invalid = SimulationScenario("duplicate", "", "description", ("condition",), ScenarioSource.USER_SUPPLIED)
    for item in (
        command(strategy, scenarios=(invalid,)),
        command(strategy, assumptions=(UserSimulationAssumption("value", "missing"),)),
    ):
        with pytest.raises(SimulationApplicationValidationError):
            service(runner).create_strategy_stress_test(db, command=item, actor_user_id=1, scope=StrategyScope(1))
    assert runner.calls == []
    assert db.execute(select(simulation_create_idempotency_table)).all() == []


@pytest.mark.parametrize("values", [
    {"scenarios": (SimulationScenario("other", "Other", "Other conditions.", ("Other.",), ScenarioSource.USER_SUPPLIED),), "assumptions": ()},
    {"scenarios": (SCENARIO,), "assumptions": (UserSimulationAssumption("Different assumption.", "adverse"),)},
])
def test_same_key_different_semantic_request_conflicts_without_provider(db, values):
    strategy = persisted_strategy(db)
    first_runner = Orchestrator()
    service(first_runner).create_strategy_stress_test(db, command=command(strategy), actor_user_id=1, scope=StrategyScope(1))
    second_runner = Orchestrator()
    with pytest.raises(SimulationApplicationConflictError):
        service(second_runner).create_strategy_stress_test(
            db, command=command(strategy, **values), actor_user_id=1, scope=StrategyScope(1),
        )
    assert second_runner.calls == [] and len(first_runner.calls) == 1


def test_same_key_different_strategy_conflicts_without_provider(db):
    first, second = persisted_strategy(db), persisted_strategy(db)
    application = service(Orchestrator())
    application.create_strategy_stress_test(db, command=command(first), actor_user_id=1, scope=StrategyScope(1))
    runner = Orchestrator()
    with pytest.raises(SimulationApplicationConflictError):
        service(runner).create_strategy_stress_test(db, command=command(second), actor_user_id=1, scope=StrategyScope(1))
    assert runner.calls == []


def test_active_claim_prevents_second_provider_execution(db):
    strategy = persisted_strategy(db)
    application = service(Orchestrator())
    cmd = command(strategy)
    from app.simulation.application import simulation_creation_fingerprint
    application.idempotency_store.claim(
        db, idempotency_key=cmd.idempotency_key, request_fingerprint=simulation_creation_fingerprint(cmd),
        actor_user_id=1, scope=StrategyScope(1),
    )
    db.commit()
    with pytest.raises(SimulationApplicationInProgressError):
        application.create_strategy_stress_test(db, command=cmd, actor_user_id=1, scope=StrategyScope(1))
    assert application.orchestrator.calls == []


def test_provider_failure_creates_no_artifacts_and_releases_for_retry(db):
    strategy = persisted_strategy(db)
    failing = Orchestrator(error=RuntimeError("private provider failure"))
    with pytest.raises(SimulationApplicationGenerationError) as captured:
        service(failing).create_strategy_stress_test(db, command=command(strategy), actor_user_id=1, scope=StrategyScope(1))
    assert "private" not in str(captured.value)
    assert db.execute(select(simulation_resource_table)).all() == []
    assert db.execute(select(simulation_run_table)).all() == []
    retry = service(Orchestrator()).create_strategy_stress_test(db, command=command(strategy), actor_user_id=1, scope=StrategyScope(1))
    assert retry.run_number == 1


def test_resource_run_and_completion_rollback_together_on_persistence_failure(db):
    strategy = persisted_strategy(db)
    class FailingRepository(SimulationRepository):
        def append_run(self, db, **values):
            raise SimulationPersistenceError("private database failure")
    runner = Orchestrator()
    with pytest.raises(SimulationApplicationPersistenceError) as captured:
        service(runner, FailingRepository()).create_strategy_stress_test(
            db, command=command(strategy), actor_user_id=1, scope=StrategyScope(1),
        )
    assert "private" not in str(captured.value)
    assert len(runner.calls) == 1
    assert db.execute(select(simulation_resource_table)).all() == []
    assert db.execute(select(simulation_run_table)).all() == []
    row = db.execute(select(simulation_create_idempotency_table)).mappings().one()
    assert row["status"] == "in_progress" and row["simulation_resource_id"] is None


def test_unexpected_persistence_failure_is_safe_and_atomic(db):
    strategy = persisted_strategy(db)
    class UnexpectedRepository(SimulationRepository):
        def append_run(self, db, **values):
            raise RuntimeError("private unexpected detail")
    with pytest.raises(SimulationApplicationInternalError) as captured:
        service(Orchestrator(), UnexpectedRepository()).create_strategy_stress_test(
            db, command=command(strategy), actor_user_id=1, scope=StrategyScope(1),
        )
    assert "private" not in str(captured.value)
    assert db.execute(select(simulation_resource_table)).all() == []
    assert db.execute(select(simulation_run_table)).all() == []


def test_absent_provider_metadata_is_valid(db):
    strategy = persisted_strategy(db)
    runner = Orchestrator()
    runner.provider = object()
    service(runner).create_strategy_stress_test(db, command=command(strategy), actor_user_id=1, scope=StrategyScope(1))
    row = db.execute(select(simulation_run_table)).mappings().one()
    assert row["provider_name"] is row["model_name"] is None


def test_real_orchestrator_repair_calls_provider_twice_but_creates_one_simulation(db):
    strategy = persisted_strategy(db)
    favorable = SimulationScenario(
        "favorable", "Favorable", "Reliability improves before expansion.",
        ("Service reliability improves.",), ScenarioSource.USER_SUPPLIED, ScenarioSeverity.LOW,
    )
    repaired = valid_output()
    repaired["assumptions_used"] = [{
        "statement": "Staffing remains fixed.",
        "provenance": "USER_SUPPLIED",
        "evidence_refs": ["evidence-1"],
    }]
    provider = RecordingProvider({}, repaired)
    application = service(SimulationOrchestrator(provider))
    result = application.create_strategy_stress_test(
        db, command=command(strategy, scenarios=(SCENARIO, favorable)),
        actor_user_id=1, scope=StrategyScope(1),
    )
    assert result.run_number == 1 and len(provider.calls) == 2
    assert len(db.execute(select(simulation_resource_table)).all()) == 1
    assert len(db.execute(select(simulation_run_table)).all()) == 1


def test_execution_envelope_lease_blocks_retry_beyond_old_window_during_two_call_repair(db, monkeypatch):
    monkeypatch.setenv("AURA_AI_TIMEOUT_SECONDS", "151")
    strategy = persisted_strategy(db)
    scope = StrategyScope(1)
    favorable = SimulationScenario(
        "favorable", "Favorable", "Reliability improves before expansion.",
        ("Service reliability improves.",), ScenarioSource.USER_SUPPLIED, ScenarioSeverity.LOW,
    )
    cmd = command(strategy, scenarios=(SCENARIO, favorable))
    started = datetime.now(timezone.utc)
    observed = []
    class ClockedStore(SimulationCreateIdempotencyStore):
        now = started

        def claim(self, db, **values):
            return super().claim(db, now=self.now, **values)

        def renew_claim(self, db, **values):
            return super().renew_claim(db, now=self.now, **values)

        def complete(self, db, **values):
            return super().complete(db, now=self.now, **values)

        def release_claim(self, db, **values):
            return super().release_claim(db, now=self.now, **values)

    store = ClockedStore()
    retry_runner = Orchestrator()

    class ConcurrentRetryProvider(RecordingProvider):
        def generate_structured(self, **kwargs):
            if len(self.calls) == 1:
                store.now = started + timedelta(seconds=301)
                with pytest.raises(SimulationApplicationInProgressError):
                    SimulationApplicationService(
                        orchestrator=retry_runner, idempotency_store=store,
                    ).create_strategy_stress_test(
                        db, command=cmd, actor_user_id=1, scope=scope,
                    )
                observed.append("blocked")
            return super().generate_structured(**kwargs)

    repaired = valid_output()
    repaired["assumptions_used"] = [{
        "statement": "Staffing remains fixed.",
        "provenance": "USER_SUPPLIED",
        "evidence_refs": ["evidence-1"],
    }]
    provider = ConcurrentRetryProvider({}, repaired)
    application = SimulationApplicationService(
        orchestrator=SimulationOrchestrator(provider), idempotency_store=store,
    )
    result = application.create_strategy_stress_test(
        db, command=cmd, actor_user_id=1, scope=scope,
    )
    assert simulation_generation_lease_duration() == timedelta(seconds=392)
    assert observed == ["blocked"]
    assert retry_runner.calls == []
    assert len(provider.calls) == 2
    assert result.run_number == 1
    assert len(db.execute(select(simulation_resource_table)).all()) == 1
    assert len(db.execute(select(simulation_run_table)).all()) == 1

    replay_provider = RecordingProvider(valid_output())
    replay = SimulationApplicationService(
        orchestrator=SimulationOrchestrator(replay_provider), idempotency_store=store,
    ).create_strategy_stress_test(db, command=cmd, actor_user_id=1, scope=scope)
    assert replay.simulation_public_id == result.simulation_public_id
    assert replay_provider.calls == []


@pytest.mark.parametrize(("configured", "expected_seconds"), [
    ("1", 110), ("151", 392), ("300", 690), ("999", 690), ("invalid", 270),
])
def test_generation_lease_respects_timeout_configuration_boundaries(monkeypatch, configured, expected_seconds):
    monkeypatch.setenv("AURA_AI_TIMEOUT_SECONDS", configured)
    assert simulation_generation_lease_duration() == timedelta(seconds=expected_seconds)


def test_stale_claim_is_recovered_by_application(db):
    strategy = persisted_strategy(db)
    cmd = command(strategy)
    application = service(Orchestrator())
    from app.simulation.application import simulation_creation_fingerprint
    application.idempotency_store.claim(
        db, idempotency_key=cmd.idempotency_key,
        request_fingerprint=simulation_creation_fingerprint(cmd), actor_user_id=1,
        scope=StrategyScope(1), now=datetime.now(timezone.utc) - timedelta(minutes=10),
    )
    db.commit()
    result = application.create_strategy_stress_test(
        db, command=cmd, actor_user_id=1, scope=StrategyScope(1),
    )
    assert result.run_number == 1 and len(application.orchestrator.calls) == 1
