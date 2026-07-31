import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from app.commercial.models import Plan, PlanFeature
from app.commercial.repositories import SqlAlchemyPlanFeatureRepository

@pytest.fixture
def session(tmp_path):
    engine=create_engine(f"sqlite:///{tmp_path / 'features.db'}")
    event.listen(engine,"connect",lambda dbapi,_: dbapi.execute("PRAGMA foreign_keys=ON"))
    Plan.metadata.create_all(engine); s=sessionmaker(bind=engine)(); yield s; s.close()

def test_plan_features_crud_relationship_and_constraints(session):
    first=Plan(code="first",name="First",seat_limit=1); second=Plan(code="second",name="Second",seat_limit=1); session.add_all([first,second]); session.commit()
    repo=SqlAlchemyPlanFeatureRepository(session)
    flag=repo.save(PlanFeature(plan_id=first.id,feature_key="api",value_type="boolean",boolean_value=True)); repo.save(PlanFeature(plan_id=first.id,feature_key="seats",value_type="integer",integer_value=5)); repo.save(PlanFeature(plan_id=second.id,feature_key="api",value_type="string",string_value="yes")); session.commit()
    assert repo.get_by_id(flag.id).boolean_value is True and repo.get_by_plan_and_key(first.id,"missing") is None
    assert len(repo.list_for_plan(first.id)) == 2 and len(first.features) == 2
    with pytest.raises(IntegrityError): repo.save(PlanFeature(plan_id=first.id,feature_key="api",value_type="boolean",boolean_value=True))
    session.rollback()
    with pytest.raises(IntegrityError): repo.save(PlanFeature(plan_id=999,feature_key="bad",value_type="integer",integer_value=1))
    session.rollback()
    with pytest.raises(IntegrityError): repo.save(PlanFeature(plan_id=first.id,feature_key="negative",value_type="integer",integer_value=-1))
    session.rollback()
    session.delete(first); session.commit(); assert repo.list_for_plan(first.id) == []
