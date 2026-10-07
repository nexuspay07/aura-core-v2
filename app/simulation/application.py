"""Application orchestration for durable Strategy Stress Tests."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import re
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError

from app.simulation.adapters import SimulationAdapterError, build_simulation_input_from_strategy_revision
from app.simulation.contracts import (
    FindingProvenance,
    ScenarioSeverity,
    ScenarioSource,
    SimulationResultV1,
    SimulationScenario,
    SimulationType,
    UserSimulationAssumption,
)
from app.simulation.idempotency import (
    SimulationCreateClaimState,
    SimulationCreateIdempotencyStore,
    SimulationIdempotencyCompletionError,
    SimulationIdempotencyError,
    simulation_create_idempotency_store,
)
from app.simulation.orchestrator import SimulationOrchestrator, simulation_orchestrator
from app.simulation.persistence import (
    PersistedSimulationResource,
    PersistedSimulationRun,
    SimulationPersistenceError,
    SimulationPersistenceNotFoundError,
    SimulationRepository,
    simulation_repository,
)
from app.simulation.serialization import simulation_to_dict
from app.strategy.contracts import StrategyScope
from app.strategy.persistence import StrategyPersistenceError, StrategyPersistenceNotFoundError, StrategyRepository, strategy_repository


_SCENARIO_KEY = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
_MAX_TEXT = 4000


@dataclass(frozen=True)
class CreateStrategyStressTestCommand:
    strategy_public_id: str
    scenarios: tuple[SimulationScenario, ...]
    user_assumptions: tuple[UserSimulationAssumption, ...] = ()
    title: str = "Strategy Stress Test"
    idempotency_key: str = ""


@dataclass(frozen=True)
class StrategyStressTestApplicationResult:
    simulation_public_id: str
    simulation_type: SimulationType
    title: str
    source_strategy_public_id: str
    source_strategy_revision: int
    source_decision_snapshot_public_id: str | None
    run_number: int
    result: SimulationResultV1
    created_at: datetime
    archived: bool


class SimulationApplicationError(ValueError):
    pass


class SimulationApplicationValidationError(SimulationApplicationError):
    pass


class SimulationApplicationNotFoundError(SimulationApplicationError):
    pass


class SimulationApplicationConflictError(SimulationApplicationError):
    pass


class SimulationApplicationInProgressError(SimulationApplicationConflictError):
    pass


class SimulationApplicationGenerationError(SimulationApplicationError):
    pass


class SimulationApplicationPersistenceError(SimulationApplicationError):
    pass


class SimulationApplicationInternalError(SimulationApplicationError):
    pass


def simulation_creation_fingerprint(command: CreateStrategyStressTestCommand) -> str:
    payload = {
        "operation": "simulation_create_strategy_stress_test",
        "version": 1,
        "strategy_public_id": command.strategy_public_id.lower(),
        "scenarios": simulation_to_dict(command.scenarios),
        "user_assumptions": simulation_to_dict(command.user_assumptions),
        "title": " ".join(command.title.split()),
    }
    canonical = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class SimulationApplicationService:
    def __init__(
        self, *, orchestrator: SimulationOrchestrator | None = None,
        simulation_repository: SimulationRepository | None = None,
        strategy_repository: StrategyRepository | None = None,
        idempotency_store: SimulationCreateIdempotencyStore | None = None,
    ) -> None:
        self.orchestrator = orchestrator or simulation_orchestrator
        self.simulation_repository = simulation_repository or globals()["simulation_repository"]
        self.strategy_repository = strategy_repository or globals()["strategy_repository"]
        self.idempotency_store = idempotency_store or simulation_create_idempotency_store

    def create_strategy_stress_test(
        self, db, *, command: CreateStrategyStressTestCommand,
        actor_user_id: int, scope: StrategyScope,
    ) -> StrategyStressTestApplicationResult:
        command = self._validate(command, actor_user_id, scope)
        fingerprint = simulation_creation_fingerprint(command)
        try:
            claim = self.idempotency_store.claim(
                db, idempotency_key=command.idempotency_key,
                request_fingerprint=fingerprint, actor_user_id=actor_user_id, scope=scope,
            )
            db.commit()
        except SimulationIdempotencyError as error:
            db.rollback()
            raise SimulationApplicationValidationError("Invalid Simulation creation request") from error
        except SQLAlchemyError as error:
            db.rollback()
            raise SimulationApplicationPersistenceError("Unable to coordinate Simulation creation") from error
        except Exception as error:
            db.rollback()
            raise SimulationApplicationInternalError("Unable to coordinate Simulation creation") from error

        if claim.state is SimulationCreateClaimState.CONFLICT:
            raise SimulationApplicationConflictError("Idempotency key conflicts with another request")
        if claim.state is SimulationCreateClaimState.IN_PROGRESS:
            raise SimulationApplicationInProgressError("Simulation creation is already in progress")
        if claim.state is SimulationCreateClaimState.COMPLETED:
            return self._completed(db, claim.simulation_resource_id, scope)

        token = claim.claim_token
        try:
            strategy = self._strategy(db, command.strategy_public_id, scope)
            execution = build_simulation_input_from_strategy_revision(
                strategy.result, strategy_schema_version=strategy.snapshot_schema_version,
                scenarios=command.scenarios, user_assumptions=command.user_assumptions,
            )
        except (StrategyPersistenceNotFoundError, StrategyPersistenceError):
            self._release(db, command, actor_user_id, scope, token)
            raise SimulationApplicationNotFoundError("Strategy not found") from None
        except (SimulationAdapterError, ValueError) as error:
            self._release(db, command, actor_user_id, scope, token)
            raise SimulationApplicationValidationError("Invalid Simulation creation request") from error
        except SQLAlchemyError as error:
            self._release(db, command, actor_user_id, scope, token)
            raise SimulationApplicationPersistenceError("Unable to resolve source Strategy") from error
        except Exception as error:
            self._release(db, command, actor_user_id, scope, token)
            raise SimulationApplicationInternalError("Unable to resolve source Strategy") from error

        try:
            if not self.idempotency_store.renew_claim(
                db, idempotency_key=command.idempotency_key, actor_user_id=actor_user_id,
                scope=scope, claim_token=token,
            ):
                db.rollback()
                raise SimulationApplicationConflictError("Simulation creation claim was lost")
            db.commit()
            generated = self.orchestrator.run(execution)
        except SimulationApplicationConflictError:
            raise
        except Exception as error:
            db.rollback()
            self._release(db, command, actor_user_id, scope, token)
            raise SimulationApplicationGenerationError("Unable to generate Simulation") from error

        try:
            provider = getattr(self.orchestrator, "provider", None)
            resource = self.simulation_repository.create_resource(
                db, execution_input=execution, title=command.title,
                scope=scope, created_by_user_id=actor_user_id,
            )
            run = self.simulation_repository.append_run(
                db, resource_public_id=resource.public_id, scope=scope,
                execution_input=execution, result=generated, created_by_user_id=actor_user_id,
                provider_name=getattr(provider, "provider_name", None),
                model_name=getattr(provider, "model_name", None),
            )
            resource_id = self.simulation_repository.get_resource_internal_id(
                db, public_id=resource.public_id, scope=scope,
            )
            self.idempotency_store.complete(
                db, idempotency_key=command.idempotency_key,
                request_fingerprint=fingerprint, actor_user_id=actor_user_id, scope=scope,
                claim_token=token, simulation_resource_id=resource_id,
            )
            db.commit()
            resource = self._resource(db, resource.public_id, scope)
            return self._result(resource, run)
        except SimulationIdempotencyCompletionError as error:
            db.rollback()
            self._release(db, command, actor_user_id, scope, token)
            raise SimulationApplicationConflictError("Simulation creation claim could not be completed") from error
        except (SimulationPersistenceError, SimulationIdempotencyError, SQLAlchemyError) as error:
            db.rollback()
            self._release(db, command, actor_user_id, scope, token)
            raise SimulationApplicationPersistenceError("Unable to persist Simulation") from error
        except Exception as error:
            db.rollback()
            self._release(db, command, actor_user_id, scope, token)
            raise SimulationApplicationInternalError("Unable to complete Simulation creation") from error

    @staticmethod
    def _validate(command, actor_user_id, scope):
        if not isinstance(command, CreateStrategyStressTestCommand):
            raise SimulationApplicationValidationError("Invalid Simulation creation request")
        if not isinstance(actor_user_id, int) or isinstance(actor_user_id, bool) or actor_user_id <= 0:
            raise SimulationApplicationValidationError("Invalid authenticated Simulation actor")
        if not isinstance(scope, StrategyScope) or scope.user_id != actor_user_id or ((scope.organization_id is None) != (scope.workspace_id is None)):
            raise SimulationApplicationValidationError("Invalid authenticated Simulation scope")
        try:
            strategy_public_id = str(UUID(command.strategy_public_id))
        except (ValueError, TypeError, AttributeError) as error:
            raise SimulationApplicationValidationError("Invalid Strategy public identifier") from error
        title = " ".join(command.title.split()) if isinstance(command.title, str) else ""
        if not title or len(title) > 255 or not isinstance(command.scenarios, tuple) or not command.scenarios:
            raise SimulationApplicationValidationError("Invalid Simulation creation request")
        if len(command.scenarios) > 6:
            raise SimulationApplicationValidationError("Invalid Simulation scenarios")
        keys = []
        for scenario in command.scenarios:
            if not isinstance(scenario, SimulationScenario) or scenario.source is not ScenarioSource.USER_SUPPLIED:
                raise SimulationApplicationValidationError("Invalid Simulation scenarios")
            texts = (scenario.name, scenario.description)
            if (
                not isinstance(scenario.key, str) or not _SCENARIO_KEY.fullmatch(scenario.key)
                or any(not isinstance(value, str) or not value.strip() or len(value) > _MAX_TEXT for value in texts)
                or not isinstance(scenario.changed_conditions, tuple)
                or not 1 <= len(scenario.changed_conditions) <= 20
                or any(not isinstance(value, str) or not value.strip() or len(value) > _MAX_TEXT for value in scenario.changed_conditions)
                or (scenario.severity is not None and not isinstance(scenario.severity, ScenarioSeverity))
            ):
                raise SimulationApplicationValidationError("Invalid Simulation scenarios")
            keys.append(scenario.key)
        if len(keys) != len(set(keys)):
            raise SimulationApplicationValidationError("Invalid Simulation scenarios")
        if not isinstance(command.user_assumptions, tuple) or len(command.user_assumptions) > 30 or any(
            not isinstance(item, UserSimulationAssumption)
            or item.provenance is not FindingProvenance.USER_SUPPLIED
            or not isinstance(item.statement, str) or not item.statement.strip()
            or len(item.statement) > _MAX_TEXT
            or (item.scenario_key is not None and item.scenario_key not in set(keys))
            for item in command.user_assumptions
        ):
            raise SimulationApplicationValidationError("Invalid Simulation assumptions")
        return CreateStrategyStressTestCommand(
            strategy_public_id, command.scenarios, command.user_assumptions,
            title, command.idempotency_key,
        )

    def _strategy(self, db, public_id, scope):
        if scope.organization_id is None:
            strategy = self.strategy_repository.get_personal_strategy_by_public_id(db, public_id=public_id, owner_user_id=scope.user_id)
        else:
            strategy = self.strategy_repository.get_workspace_strategy_by_public_id(
                db, public_id=public_id, organization_id=scope.organization_id, workspace_id=scope.workspace_id,
            )
        if strategy.archived_at is not None:
            raise StrategyPersistenceNotFoundError("Strategy not found")
        return strategy

    def _resource(self, db, public_id, scope):
        if scope.organization_id is None:
            return self.simulation_repository.get_personal_resource(db, public_id=public_id, owner_user_id=scope.user_id)
        return self.simulation_repository.get_workspace_resource(
            db, public_id=public_id, organization_id=scope.organization_id, workspace_id=scope.workspace_id,
        )

    def _completed(self, db, resource_id, scope):
        try:
            if not isinstance(resource_id, int):
                raise SimulationPersistenceNotFoundError("Simulation not found")
            if scope.organization_id is None:
                resource = self.simulation_repository.get_personal_resource_by_internal_id(db, resource_id=resource_id, owner_user_id=scope.user_id)
            else:
                resource = self.simulation_repository.get_workspace_resource_by_internal_id(
                    db, resource_id=resource_id, organization_id=scope.organization_id, workspace_id=scope.workspace_id,
                )
            run = self.simulation_repository.get_latest_run(db, resource_public_id=resource.public_id, scope=scope)
            return self._result(resource, run)
        except (SimulationPersistenceError, SQLAlchemyError) as error:
            raise SimulationApplicationPersistenceError("Unable to resolve completed Simulation") from error

    def _release(self, db, command, actor_user_id, scope, token):
        try:
            self.idempotency_store.release_claim(
                db, idempotency_key=command.idempotency_key, actor_user_id=actor_user_id,
                scope=scope, claim_token=token,
            )
            db.commit()
        except Exception:
            db.rollback()

    @staticmethod
    def _result(resource: PersistedSimulationResource, run: PersistedSimulationRun):
        return StrategyStressTestApplicationResult(
            simulation_public_id=resource.public_id, simulation_type=resource.simulation_type,
            title=resource.title, source_strategy_public_id=resource.source_strategy_public_id,
            source_strategy_revision=resource.source_strategy_revision,
            source_decision_snapshot_public_id=resource.source_decision_snapshot_public_id,
            run_number=run.run_number, result=run.result, created_at=resource.created_at,
            archived=resource.archived_at is not None,
        )


simulation_application_service = SimulationApplicationService()
