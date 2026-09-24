import pytest
from sqlalchemy import create_engine, event, insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from app.db.database import metadata
from app.db.decision_execution_snapshot_table import decision_execution_snapshot_table
from app.db.intelligence_session_table import intelligence_session_table
from app.db.organization_table import organization_table
from app.db.user_table import user_table
from app.db.workspace_table import workspace_table
from app.intelligence_v2.decision_snapshot import CanonicalDecisionSnapshotV1
from app.intelligence_v2.decision_snapshot_repository import DecisionSnapshotUnavailableError, decision_execution_snapshot_repository
from tests.strategy.test_adapters import decision_artifacts

@pytest.fixture
def db():
    engine=create_engine("sqlite://"); event.listen(engine,"connect",lambda c,_:c.execute("PRAGMA foreign_keys=ON")); metadata.create_all(engine); session=sessionmaker(bind=engine)()
    session.execute(insert(user_table), [{"id":1,"email":"one@snapshot","password_hash":"x"},{"id":2,"email":"two@snapshot","password_hash":"x"}])
    session.execute(insert(organization_table), [{"id":1,"name":"One","slug":"one-snapshot","owner_user_id":1,"account_type":"personal","plan":"free","subscription_status":"inactive","is_active":True},{"id":2,"name":"Two","slug":"two-snapshot","owner_user_id":2,"account_type":"personal","plan":"free","subscription_status":"inactive","is_active":True}])
    session.execute(insert(workspace_table), [{"id":1,"organization_id":1,"created_by_user_id":1,"name":"One","slug":"one-snapshot","workspace_type":"personal","is_active":True},{"id":2,"organization_id":2,"created_by_user_id":2,"name":"Two","slug":"two-snapshot","workspace_type":"personal","is_active":True}])
    session.execute(insert(intelligence_session_table), [{"id":1,"organization_id":1,"workspace_id":1,"created_by_user_id":1,"title":"One","goal":"One","session_type":"personal_ask_v2","status":"completed","is_active":True},{"id":2,"organization_id":1,"workspace_id":1,"created_by_user_id":1,"title":"Two","goal":"Two","session_type":"personal_ask_v2","status":"completed","is_active":True}]); session.commit()
    yield session; session.close(); engine.dispose()

def test_versions_hydration_and_exact_scope(db):
    snapshot=CanonicalDecisionSnapshotV1.capture(*decision_artifacts())
    first=decision_execution_snapshot_repository.create(db,snapshot=snapshot,intelligence_session_id=1,user_id=1,organization_id=1,workspace_id=1)
    second=decision_execution_snapshot_repository.create(db,snapshot=snapshot,intelligence_session_id=1,user_id=1,organization_id=1,workspace_id=1)
    other=decision_execution_snapshot_repository.create(db,snapshot=snapshot,intelligence_session_id=2,user_id=1,organization_id=1,workspace_id=1)
    assert (first.snapshot_version,second.snapshot_version,other.snapshot_version)==(1,2,1)
    assert decision_execution_snapshot_repository.latest_for_session_owned(db,intelligence_session_id=1,user_id=1,organization_id=1,workspace_id=1).id==second.id
    with pytest.raises(DecisionSnapshotUnavailableError): decision_execution_snapshot_repository.get_owned(db,snapshot_id=first.id,user_id=2,organization_id=2,workspace_id=2)
    with pytest.raises(DecisionSnapshotUnavailableError): decision_execution_snapshot_repository.create(db,snapshot=snapshot,intelligence_session_id=1,user_id=2,organization_id=2,workspace_id=2)

def test_database_prevents_duplicate_session_version(db):
    snapshot=CanonicalDecisionSnapshotV1.capture(*decision_artifacts()).to_dict()
    values=dict(public_id="00000000-0000-4000-8000-000000000099",intelligence_session_id=1,user_id=1,organization_id=1,workspace_id=1,snapshot_version=1,snapshot_schema_version=1,canonical_decision_json=snapshot)
    db.execute(insert(decision_execution_snapshot_table).values(**values)); db.commit()
    with pytest.raises(IntegrityError):
        db.execute(insert(decision_execution_snapshot_table).values(**{**values,"public_id":"00000000-0000-4000-8000-000000000100"})); db.commit()
