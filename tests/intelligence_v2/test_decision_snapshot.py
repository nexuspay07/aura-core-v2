import json
import pytest
from app.intelligence_v2.decision_snapshot import CanonicalDecisionSnapshotV1, DecisionSnapshotValidationError
from app.strategy.adapters import build_strategy_input, build_strategy_input_from_snapshot
from app.strategy.contracts import StrategyScope
from tests.strategy.test_adapters import decision_artifacts

def test_explicit_snapshot_is_deterministic_private_and_round_trips_strategy_input():
    state, execution = decision_artifacts(rich=True)
    snapshot = CanonicalDecisionSnapshotV1.capture(state, execution)
    encoded = json.dumps(snapshot.to_dict(), sort_keys=True, separators=(",", ":"))
    hydrated = CanonicalDecisionSnapshotV1.from_dict(json.loads(encoded))
    assert snapshot == hydrated
    assert build_strategy_input(state, execution) == build_strategy_input_from_snapshot(hydrated, scope=StrategyScope(11, 22, 33))
    for secret in ("PRIVATE CONVERSATION", "PRIVATE PROVIDER", "PRIVATE TOKEN", "PRIVATE CREDENTIAL", "PRIVATE SIMULATION", "PRIVATE RAW DOCUMENT BODY"):
        assert secret not in encoded

def test_snapshot_rejects_unknown_fields_malformed_data_and_versions():
    snapshot = CanonicalDecisionSnapshotV1.capture(*decision_artifacts()).to_dict()
    with pytest.raises(DecisionSnapshotValidationError, match="fields"):
        CanonicalDecisionSnapshotV1.from_dict({**snapshot, "raw_provider_response": "secret"})
    with pytest.raises(DecisionSnapshotValidationError, match="schema version"):
        CanonicalDecisionSnapshotV1.from_dict({**snapshot, "schema_version": 2})
    with pytest.raises(DecisionSnapshotValidationError):
        CanonicalDecisionSnapshotV1.from_dict({**snapshot, "objective": " "})

def test_snapshot_preserves_approved_alternative_details():
    snapshot = CanonicalDecisionSnapshotV1.capture(*decision_artifacts(rich=True))
    assert snapshot.alternatives[0]["benefits"] == ["Retention"]
    assert snapshot.alternatives[0]["downsides"] == ["Delay"]
    assert snapshot.alternatives[0]["evidence_ids"] == ["evidence-1"]
