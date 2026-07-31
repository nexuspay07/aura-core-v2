import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from app.commercial.models import Plan
from app.commercial.repositories import SqlAlchemyPlanRepository

@pytest.fixture
def repo(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'plans.db'}")
    Plan.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield SqlAlchemyPlanRepository(session), session
    session.close()

def test_plan_repository_crud_and_constraints(repo):
    repository, session = repo
    plan = repository.save(Plan(code="pro", name="Professional", seat_limit=5))
    session.commit()
    assert repository.get_by_code("pro").id == plan.id
    assert repository.get_by_code("missing") is None
    plan.is_active = False; session.commit()
    assert repository.list_active() == []
    with pytest.raises(IntegrityError):
        repository.save(Plan(code="pro", name="Duplicate", seat_limit=1))
    session.rollback()
    with pytest.raises(IntegrityError):
        repository.save(Plan(code="bad", name="Bad", seat_limit=-1))
    session.rollback()
