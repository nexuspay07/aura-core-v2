"""Tenant-safe persistence for canonical Simulation resources and runs."""

from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import datetime, timezone
import re
from typing import Any, Mapping
from uuid import uuid4

from sqlalchemy import select, update

from app.db.decision_execution_snapshot_table import decision_execution_snapshot_table
from app.db.simulation_resource_table import simulation_resource_table, simulation_run_table
from app.db.strategy_resource_table import strategy_resource_table, strategy_revision_table
from app.db.workspace_table import workspace_table
from app.simulation.contracts import (
    FindingProvenance,
    ScenarioSeverity,
    ScenarioSource,
    SimulationExecutionInputV1,
    SimulationFinding,
    SimulationInputV1,
    SimulationLimitation,
    SimulationResultV1,
    SimulationScenario,
    SimulationSourceProvenanceV1,
    SimulationSourceType,
    SimulationType,
    StrategyStressResult,
    UserSimulationAssumption,
)
from app.simulation.quality import validate_simulation_result_quality
from app.simulation.serialization import simulation_to_dict
from app.simulation.validation import validate_simulation_execution_input, validate_simulation_result
from app.strategy.contracts import (
    ConfidenceLevel,
    EvidenceReference,
    StrategyAssumption,
    StrategyConstraint,
    StrategyPhase,
    StrategyResource,
    StrategyRisk,
    StrategyScope,
    SuccessMeasure,
)


SIMULATION_ENGINE_VERSION = "strategy_stress_test_v1"
DETERMINISM_MODE = "model_assisted"
_SAFE_METADATA = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]*$")


class SimulationPersistenceError(ValueError):
    """Simulation persistence input or durable data violates its contract."""


class SimulationPersistenceNotFoundError(SimulationPersistenceError):
    """No Simulation exists in the authorized tenant scope."""


class SimulationPersistenceConflictError(SimulationPersistenceError):
    """A Simulation resource changed concurrently."""


@dataclass(frozen=True)
class PersistedSimulationResource:
    public_id: str
    title: str
    simulation_type: SimulationType
    scope: StrategyScope
    created_by_user_id: int
    source_strategy_public_id: str
    source_strategy_revision: int
    source_decision_snapshot_public_id: str | None
    current_run_number: int
    lock_version: int
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class PersistedSimulationRun:
    resource_public_id: str
    run_number: int
    execution_input: SimulationExecutionInputV1
    result: SimulationResultV1
    input_schema_version: int
    result_schema_version: int
    engine_version: str
    provider_name: str | None
    model_name: str | None
    determinism_mode: str
    created_by_user_id: int
    created_at: datetime


def _object(value: object, contract: type, name: str) -> Mapping[str, Any]:
    expected = {item.name for item in fields(contract)}
    if not isinstance(value, Mapping) or set(value) != expected:
        raise SimulationPersistenceError(f"Malformed Simulation snapshot: {name}")
    return value


def _list(value: object, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise SimulationPersistenceError(f"Malformed Simulation snapshot: {name}")
    return value


def _optional_text(value: object, name: str) -> str | None:
    if value is None or isinstance(value, str):
        return value
    raise SimulationPersistenceError(f"Malformed Simulation snapshot: {name}")


def _items(value, contract, name, factory):
    return tuple(factory(_object(item, contract, name)) for item in _list(value, name))


def _phase(item):
    return StrategyPhase(
        item["order"], item["name"], item["purpose"],
        tuple(_list(item["focus_areas"], "phase.focus_areas")),
        _optional_text(item["milestone_intent"], "phase.milestone_intent"),
    )


def _finding(item):
    return SimulationFinding(
        item["statement"], FindingProvenance(item["provenance"]),
        tuple(_list(item["evidence_refs"], "finding.evidence_refs")),
    )


def hydrate_simulation_execution_input(snapshot: object) -> SimulationExecutionInputV1:
    """Hydrate and validate an immutable canonical execution-input snapshot."""

    try:
        root = _object(snapshot, SimulationExecutionInputV1, "execution_input")
        provenance = _object(root["provenance"], SimulationSourceProvenanceV1, "provenance")
        source = _object(root["simulation_input"], SimulationInputV1, "simulation_input")
        value = SimulationExecutionInputV1(
            provenance=SimulationSourceProvenanceV1(
                strategy_public_id=provenance["strategy_public_id"],
                strategy_revision=provenance["strategy_revision"],
                strategy_schema_version=provenance["strategy_schema_version"],
                source_type=SimulationSourceType(provenance["source_type"]),
            ),
            simulation_input=SimulationInputV1(
                objective=source["objective"],
                chosen_direction=source["chosen_direction"],
                strategic_approach=source["strategic_approach"],
                phases=_items(source["phases"], StrategyPhase, "phase", _phase),
                success_measures=_items(
                    source["success_measures"], SuccessMeasure, "success_measure",
                    lambda item: SuccessMeasure(item["condition"], _optional_text(item["evidence_ref"], "success_measure.evidence_ref")),
                ),
                scenarios=_items(
                    source["scenarios"], SimulationScenario, "scenario",
                    lambda item: SimulationScenario(
                        item["key"], item["name"], item["description"],
                        tuple(_list(item["changed_conditions"], "scenario.changed_conditions")),
                        ScenarioSource(item["source"]),
                        ScenarioSeverity(item["severity"]) if item["severity"] is not None else None,
                    ),
                ),
                constraints=_items(
                    source["constraints"], StrategyConstraint, "constraint",
                    lambda item: StrategyConstraint(item["constraint_id"], item["statement"]),
                ),
                resources=_items(
                    source["resources"], StrategyResource, "resource",
                    lambda item: StrategyResource(item["name"], item["description"]),
                ),
                risks=_items(
                    source["risks"], StrategyRisk, "risk",
                    lambda item: StrategyRisk(item["risk"], _optional_text(item["mitigation"], "risk.mitigation")),
                ),
                strategy_assumptions=_items(
                    source["strategy_assumptions"], StrategyAssumption, "strategy_assumption",
                    lambda item: StrategyAssumption(item["statement"], item["source"]),
                ),
                uncertainties=tuple(_list(source["uncertainties"], "uncertainties")),
                change_conditions=tuple(_list(source["change_conditions"], "change_conditions")),
                time_horizon=_optional_text(source["time_horizon"], "time_horizon"),
                evidence_refs=_items(
                    source["evidence_refs"], EvidenceReference, "evidence",
                    lambda item: EvidenceReference(item["evidence_id"], _optional_text(item["citation_label"], "evidence.citation_label")),
                ),
                user_assumptions=_items(
                    source["user_assumptions"], UserSimulationAssumption, "user_assumption",
                    lambda item: UserSimulationAssumption(
                        item["statement"], _optional_text(item["scenario_key"], "user_assumption.scenario_key"),
                        FindingProvenance(item["provenance"]),
                    ),
                ),
                simulation_type=SimulationType(source["simulation_type"]),
                schema_version=source["schema_version"],
            ),
        )
        validate_simulation_execution_input(value)
        return value
    except SimulationPersistenceError:
        raise
    except (KeyError, TypeError, ValueError) as error:
        raise SimulationPersistenceError("Malformed Simulation execution-input snapshot") from error


def hydrate_simulation_result(snapshot: object, source: SimulationExecutionInputV1) -> SimulationResultV1:
    """Hydrate the accepted canonical result and reapply its trust boundary."""

    try:
        root = _object(snapshot, SimulationResultV1, "result")
        value = SimulationResultV1(
            scenario_results=_items(
                root["scenario_results"], StrategyStressResult, "scenario_result",
                lambda item: StrategyStressResult(
                    scenario_key=item["scenario_key"],
                    elements_under_stress=_items(item["elements_under_stress"], SimulationFinding, "finding", _finding),
                    plausible_effects=_items(item["plausible_effects"], SimulationFinding, "finding", _finding),
                    sensitivity=ScenarioSeverity(item["sensitivity"]),
                    constraint_conflicts=_items(item["constraint_conflicts"], SimulationFinding, "finding", _finding),
                    risk_observations=_items(item["risk_observations"], SimulationFinding, "finding", _finding),
                    mitigation_observations=_items(item["mitigation_observations"], SimulationFinding, "finding", _finding),
                    phase_sensitivities=_items(item["phase_sensitivities"], SimulationFinding, "finding", _finding),
                    upside_conditions=_items(item["upside_conditions"], SimulationFinding, "finding", _finding),
                    downside_conditions=_items(item["downside_conditions"], SimulationFinding, "finding", _finding),
                    change_condition_triggers=_items(item["change_condition_triggers"], SimulationFinding, "finding", _finding),
                ),
            ),
            cross_scenario_comparison=_items(root["cross_scenario_comparison"], SimulationFinding, "finding", _finding),
            assumptions_used=_items(root["assumptions_used"], SimulationFinding, "finding", _finding),
            uncertainties=_items(root["uncertainties"], SimulationFinding, "finding", _finding),
            limitations=_items(
                root["limitations"], SimulationLimitation, "limitation",
                lambda item: SimulationLimitation(item["code"], item["statement"], FindingProvenance(item["provenance"])),
            ),
            confidence=ConfidenceLevel(root["confidence"]),
            confidence_rationale=tuple(_list(root["confidence_rationale"], "confidence_rationale")),
            evidence_refs=_items(
                root["evidence_refs"], EvidenceReference, "evidence",
                lambda item: EvidenceReference(item["evidence_id"], _optional_text(item["citation_label"], "evidence.citation_label")),
            ),
            simulation_type=SimulationType(root["simulation_type"]),
            schema_version=root["schema_version"],
        )
        validate_simulation_result(value, source.simulation_input)
        validate_simulation_result_quality(source, value)
        return value
    except SimulationPersistenceError:
        raise
    except (KeyError, TypeError, ValueError) as error:
        raise SimulationPersistenceError("Malformed Simulation result snapshot") from error


def _safe_optional_metadata(value: object, name: str, maximum: int) -> str | None:
    if value is None:
        return None
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value) > maximum
        or not _SAFE_METADATA.fullmatch(value.strip())
    ):
        raise SimulationPersistenceError(f"{name} must be meaningful and bounded when supplied")
    return value.strip()


class SimulationRepository:
    """Persist and retrieve Simulations only within exact authorized scopes."""

    @staticmethod
    def _scope(db, scope: StrategyScope, created_by_user_id: int) -> dict[str, int | None]:
        if created_by_user_id != scope.user_id:
            raise SimulationPersistenceError("Simulation creator must match the authorized scope user")
        if scope.organization_id is None and scope.workspace_id is None:
            return {"owner_user_id": scope.user_id, "organization_id": None, "workspace_id": None}
        if scope.organization_id is None or scope.workspace_id is None:
            raise SimulationPersistenceError("Simulation scope must be personal or a complete workspace scope")
        workspace = db.execute(select(workspace_table.c.id).where(
            workspace_table.c.id == scope.workspace_id,
            workspace_table.c.organization_id == scope.organization_id,
        )).first()
        if not workspace:
            raise SimulationPersistenceError("Workspace does not belong to the Simulation organization")
        return {"owner_user_id": None, "organization_id": scope.organization_id, "workspace_id": scope.workspace_id}

    @staticmethod
    def _title(value: object) -> str:
        title = " ".join(value.split()) if isinstance(value, str) else ""
        if not title or len(title) > 255:
            raise SimulationPersistenceError("Simulation title must contain 1 to 255 characters")
        return title

    def create_resource(
        self, db, *, execution_input: SimulationExecutionInputV1, title: str,
        scope: StrategyScope, created_by_user_id: int,
    ) -> PersistedSimulationResource:
        validate_simulation_execution_input(execution_input)
        tenancy = self._scope(db, scope, created_by_user_id)
        provenance = execution_input.provenance
        conditions = [
            strategy_resource_table.c.public_id == provenance.strategy_public_id,
            strategy_resource_table.c.archived_at.is_(None),
        ]
        if scope.organization_id is None:
            conditions.extend([
                strategy_resource_table.c.owner_user_id == scope.user_id,
                strategy_resource_table.c.organization_id.is_(None),
                strategy_resource_table.c.workspace_id.is_(None),
            ])
        else:
            conditions.extend([
                strategy_resource_table.c.owner_user_id.is_(None),
                strategy_resource_table.c.organization_id == scope.organization_id,
                strategy_resource_table.c.workspace_id == scope.workspace_id,
            ])
        strategy = db.execute(select(strategy_resource_table).where(*conditions)).mappings().first()
        if not strategy:
            raise SimulationPersistenceNotFoundError("Source Strategy not found")
        revision = db.execute(select(strategy_revision_table).where(
            strategy_revision_table.c.strategy_id == strategy["id"],
            strategy_revision_table.c.revision_number == provenance.strategy_revision,
        )).mappings().first()
        if not revision:
            raise SimulationPersistenceError("Source Strategy revision does not belong to the Strategy")
        if revision["snapshot_schema_version"] != provenance.strategy_schema_version:
            raise SimulationPersistenceError("Source Strategy schema version does not match provenance")
        snapshot_public_id = None
        snapshot_id = revision["source_decision_snapshot_id"]
        if snapshot_id is not None:
            snapshot = db.execute(select(decision_execution_snapshot_table).where(
                decision_execution_snapshot_table.c.id == snapshot_id,
            )).mappings().first()
            if not snapshot:
                raise SimulationPersistenceError("Source Decision snapshot lineage is missing")
            if scope.organization_id is not None and (
                snapshot["user_id"] != scope.user_id
                or snapshot["organization_id"] != scope.organization_id
                or snapshot["workspace_id"] != scope.workspace_id
            ):
                raise SimulationPersistenceError("Source Decision snapshot lineage does not match Strategy scope")
            snapshot_public_id = snapshot["public_id"]

        insert = db.execute(simulation_resource_table.insert().values(
            public_id=str(uuid4()), title=self._title(title),
            simulation_type=execution_input.simulation_input.simulation_type.value,
            created_by_user_id=created_by_user_id,
            source_strategy_id=strategy["id"],
            source_strategy_revision_id=revision["id"],
            source_decision_snapshot_id=snapshot_id,
            current_run_number=0, lock_version=1, **tenancy,
        ))
        return self._hydrate_resource(db, insert.inserted_primary_key[0], snapshot_public_id)

    def append_run(
        self, db, *, resource_public_id: str, scope: StrategyScope,
        execution_input: SimulationExecutionInputV1, result: SimulationResultV1,
        created_by_user_id: int, provider_name: str | None = None,
        model_name: str | None = None,
    ) -> PersistedSimulationRun:
        validate_simulation_execution_input(execution_input)
        validate_simulation_result(result, execution_input.simulation_input)
        validate_simulation_result_quality(execution_input, result)
        safe_provider_name = _safe_optional_metadata(provider_name, "provider_name", 128)
        safe_model_name = _safe_optional_metadata(model_name, "model_name", 255)
        execution_snapshot = simulation_to_dict(execution_input)
        result_snapshot = simulation_to_dict(result)
        resource = self._resource_row(db, resource_public_id, scope)
        if resource["archived_at"] is not None:
            raise SimulationPersistenceError("Archived Simulation cannot accept runs")
        revision = db.execute(select(strategy_revision_table).where(
            strategy_revision_table.c.id == resource["source_strategy_revision_id"],
            strategy_revision_table.c.strategy_id == resource["source_strategy_id"],
        )).mappings().one()
        strategy = db.execute(select(strategy_resource_table).where(
            strategy_resource_table.c.id == resource["source_strategy_id"],
        )).mappings().one()
        provenance = execution_input.provenance
        if (
            provenance.strategy_public_id != strategy["public_id"]
            or provenance.strategy_revision != revision["revision_number"]
            or provenance.strategy_schema_version != revision["snapshot_schema_version"]
        ):
            raise SimulationPersistenceError("Execution input does not match pinned Strategy revision")
        if created_by_user_id != scope.user_id:
            raise SimulationPersistenceError("Simulation run creator must match authorized scope user")
        run_number = resource["current_run_number"] + 1
        now = datetime.now(timezone.utc)
        changed = db.execute(update(simulation_resource_table).where(
            simulation_resource_table.c.id == resource["id"],
            simulation_resource_table.c.lock_version == resource["lock_version"],
            simulation_resource_table.c.current_run_number == resource["current_run_number"],
        ).values(
            current_run_number=run_number,
            lock_version=simulation_resource_table.c.lock_version + 1,
            updated_at=now,
        ))
        if changed.rowcount != 1:
            raise SimulationPersistenceConflictError("Simulation run append conflicted")
        inserted = db.execute(simulation_run_table.insert().values(
            simulation_resource_id=resource["id"], run_number=run_number,
            canonical_execution_input_json=execution_snapshot,
            canonical_result_json=result_snapshot,
            input_schema_version=execution_input.simulation_input.schema_version,
            result_schema_version=result.schema_version,
            engine_version=SIMULATION_ENGINE_VERSION,
            provider_name=safe_provider_name,
            model_name=safe_model_name,
            determinism_mode=DETERMINISM_MODE,
            created_by_user_id=created_by_user_id,
        ))
        return self._hydrate_run(db, inserted.inserted_primary_key[0], resource_public_id)

    def get_personal_resource(self, db, *, public_id: str, owner_user_id: int):
        row = self._personal_row(db, public_id, owner_user_id)
        return self._hydrate_resource(db, row["id"])

    def get_workspace_resource(self, db, *, public_id: str, organization_id: int, workspace_id: int):
        row = self._workspace_row(db, public_id, organization_id, workspace_id)
        return self._hydrate_resource(db, row["id"])

    def get_personal_resource_by_internal_id(self, db, *, resource_id: int, owner_user_id: int):
        row = db.execute(select(simulation_resource_table).where(
            simulation_resource_table.c.id == resource_id,
            simulation_resource_table.c.owner_user_id == owner_user_id,
            simulation_resource_table.c.organization_id.is_(None),
            simulation_resource_table.c.workspace_id.is_(None),
        )).mappings().first()
        if not row:
            raise SimulationPersistenceNotFoundError("Simulation not found")
        return self._hydrate_resource(db, row["id"])

    def get_workspace_resource_by_internal_id(
        self, db, *, resource_id: int, organization_id: int, workspace_id: int,
    ):
        row = db.execute(select(simulation_resource_table).where(
            simulation_resource_table.c.id == resource_id,
            simulation_resource_table.c.owner_user_id.is_(None),
            simulation_resource_table.c.organization_id == organization_id,
            simulation_resource_table.c.workspace_id == workspace_id,
        )).mappings().first()
        if not row:
            raise SimulationPersistenceNotFoundError("Simulation not found")
        return self._hydrate_resource(db, row["id"])

    def get_resource_internal_id(self, db, *, public_id: str, scope: StrategyScope) -> int:
        """Resolve repository-internal identity only for an exact authorized scope."""
        return self._resource_row(db, public_id, scope)["id"]

    def get_latest_run(self, db, *, resource_public_id: str, scope: StrategyScope):
        resource = self._resource_row(db, resource_public_id, scope)
        if resource["current_run_number"] == 0:
            raise SimulationPersistenceNotFoundError("Simulation run not found")
        row = db.execute(select(simulation_run_table).where(
            simulation_run_table.c.simulation_resource_id == resource["id"],
            simulation_run_table.c.run_number == resource["current_run_number"],
        )).mappings().first()
        if not row:
            raise SimulationPersistenceError("Simulation current run is missing")
        return self._hydrate_run(db, row["id"], resource_public_id)

    def list_personal_resources(self, db, *, owner_user_id: int, limit: int = 50):
        return self._list(db, (
            simulation_resource_table.c.owner_user_id == owner_user_id,
            simulation_resource_table.c.organization_id.is_(None),
            simulation_resource_table.c.workspace_id.is_(None),
        ), limit)

    def list_workspace_resources(self, db, *, organization_id: int, workspace_id: int, limit: int = 50):
        return self._list(db, (
            simulation_resource_table.c.owner_user_id.is_(None),
            simulation_resource_table.c.organization_id == organization_id,
            simulation_resource_table.c.workspace_id == workspace_id,
        ), limit)

    def archive_personal_resource(self, db, *, public_id: str, owner_user_id: int, expected_lock_version: int):
        row = self._personal_row(db, public_id, owner_user_id)
        return self._archive(db, row, expected_lock_version)

    def archive_workspace_resource(self, db, *, public_id: str, organization_id: int, workspace_id: int, expected_lock_version: int):
        row = self._workspace_row(db, public_id, organization_id, workspace_id)
        return self._archive(db, row, expected_lock_version)

    def _resource_row(self, db, public_id: str, scope: StrategyScope):
        if scope.organization_id is None and scope.workspace_id is None:
            return self._personal_row(db, public_id, scope.user_id)
        if scope.organization_id is None or scope.workspace_id is None:
            raise SimulationPersistenceError("Simulation scope must be complete")
        return self._workspace_row(db, public_id, scope.organization_id, scope.workspace_id)

    @staticmethod
    def _personal_row(db, public_id, owner_user_id):
        row = db.execute(select(simulation_resource_table).where(
            simulation_resource_table.c.public_id == public_id,
            simulation_resource_table.c.owner_user_id == owner_user_id,
            simulation_resource_table.c.organization_id.is_(None),
            simulation_resource_table.c.workspace_id.is_(None),
        )).mappings().first()
        if not row:
            raise SimulationPersistenceNotFoundError("Simulation not found")
        return row

    @staticmethod
    def _workspace_row(db, public_id, organization_id, workspace_id):
        row = db.execute(select(simulation_resource_table).where(
            simulation_resource_table.c.public_id == public_id,
            simulation_resource_table.c.owner_user_id.is_(None),
            simulation_resource_table.c.organization_id == organization_id,
            simulation_resource_table.c.workspace_id == workspace_id,
        )).mappings().first()
        if not row:
            raise SimulationPersistenceNotFoundError("Simulation not found")
        return row

    def _list(self, db, conditions, limit):
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100:
            raise SimulationPersistenceError("Simulation list limit must be between 1 and 100")
        rows = db.execute(select(simulation_resource_table).where(
            *conditions, simulation_resource_table.c.archived_at.is_(None),
        ).order_by(
            simulation_resource_table.c.updated_at.desc(), simulation_resource_table.c.id.desc(),
        ).limit(limit)).mappings().all()
        return [self._hydrate_resource(db, row["id"]) for row in rows]

    def _archive(self, db, row, expected_lock_version):
        if not isinstance(expected_lock_version, int) or isinstance(expected_lock_version, bool) or expected_lock_version <= 0:
            raise SimulationPersistenceError("Expected lock version must be positive")
        if row["archived_at"] is None:
            now = datetime.now(timezone.utc)
            changed = db.execute(update(simulation_resource_table).where(
                simulation_resource_table.c.id == row["id"],
                simulation_resource_table.c.lock_version == expected_lock_version,
                simulation_resource_table.c.archived_at.is_(None),
            ).values(
                archived_at=now, updated_at=now,
                lock_version=simulation_resource_table.c.lock_version + 1,
            ))
            if changed.rowcount != 1:
                raise SimulationPersistenceConflictError("Simulation lock version is stale")
        return self._hydrate_resource(db, row["id"])

    @staticmethod
    def _hydrate_resource(db, resource_id, snapshot_public_id=None):
        row = db.execute(select(simulation_resource_table).where(
            simulation_resource_table.c.id == resource_id,
        )).mappings().one()
        strategy = db.execute(select(strategy_resource_table).where(
            strategy_resource_table.c.id == row["source_strategy_id"],
        )).mappings().one()
        revision = db.execute(select(strategy_revision_table).where(
            strategy_revision_table.c.id == row["source_strategy_revision_id"],
            strategy_revision_table.c.strategy_id == strategy["id"],
        )).mappings().first()
        if not revision:
            raise SimulationPersistenceError("Pinned Strategy revision is invalid")
        if row["source_decision_snapshot_id"] != revision["source_decision_snapshot_id"]:
            raise SimulationPersistenceError("Pinned Decision snapshot does not match Strategy revision")
        if snapshot_public_id is None and row["source_decision_snapshot_id"] is not None:
            snapshot_public_id = db.execute(select(decision_execution_snapshot_table.c.public_id).where(
                decision_execution_snapshot_table.c.id == row["source_decision_snapshot_id"],
            )).scalar_one()
        scope = StrategyScope(
            user_id=row["owner_user_id"] or row["created_by_user_id"],
            organization_id=row["organization_id"], workspace_id=row["workspace_id"],
        )
        return PersistedSimulationResource(
            public_id=row["public_id"], title=row["title"],
            simulation_type=SimulationType(row["simulation_type"]), scope=scope,
            created_by_user_id=row["created_by_user_id"],
            source_strategy_public_id=strategy["public_id"],
            source_strategy_revision=revision["revision_number"],
            source_decision_snapshot_public_id=snapshot_public_id,
            current_run_number=row["current_run_number"], lock_version=row["lock_version"],
            archived_at=row["archived_at"], created_at=row["created_at"], updated_at=row["updated_at"],
        )

    @staticmethod
    def _hydrate_run(db, run_id, resource_public_id):
        row = db.execute(select(simulation_run_table).where(simulation_run_table.c.id == run_id)).mappings().one()
        execution_input = hydrate_simulation_execution_input(row["canonical_execution_input_json"])
        result = hydrate_simulation_result(row["canonical_result_json"], execution_input)
        if row["input_schema_version"] != execution_input.simulation_input.schema_version or row["result_schema_version"] != result.schema_version:
            raise SimulationPersistenceError("Simulation run schema metadata does not match snapshots")
        return PersistedSimulationRun(
            resource_public_id=resource_public_id, run_number=row["run_number"],
            execution_input=execution_input, result=result,
            input_schema_version=row["input_schema_version"], result_schema_version=row["result_schema_version"],
            engine_version=row["engine_version"], provider_name=row["provider_name"], model_name=row["model_name"],
            determinism_mode=row["determinism_mode"], created_by_user_id=row["created_by_user_id"],
            created_at=row["created_at"],
        )


simulation_repository = SimulationRepository()
