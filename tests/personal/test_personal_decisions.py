from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, event, insert, select
from sqlalchemy.orm import sessionmaker

from app.db.database import metadata
from app.db.intelligence_session_table import intelligence_session_table
from app.db.organization_table import organization_table
from app.db.personal_decision_table import personal_decision_table
from app.db.user_table import user_table
from app.db.workspace_table import workspace_table
from app.personal.decisions import PersonalDecisionNotFoundError, PersonalDecisionTransitionError, display_title, personal_decision_service


def test_personal_display_titles_are_concise_without_mutating_question():
    question = "I have savings and need a reliable car. Should I buy this car now, choose a cheaper one, or wait?"
    assert display_title(question, "major_purchase") == "Buying a car"
    assert display_title("Should I take job offer A or job offer B?", "career_decision") == "Choosing between job offers"


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    event.listen(engine, "connect", lambda connection, _: connection.execute("PRAGMA foreign_keys=ON"))
    metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.execute(insert(user_table), [{"id": 1, "email": "one@test", "password_hash": "x"}, {"id": 2, "email": "two@test", "password_hash": "x"}])
    session.execute(insert(organization_table), [{"id": 1, "name": "Personal Space", "slug": "personal", "owner_user_id": 1, "account_type": "personal", "plan": "free", "subscription_status": "inactive", "is_active": True}, {"id": 2, "name": "Other", "slug": "other", "owner_user_id": 2, "account_type": "personal", "plan": "free", "subscription_status": "inactive", "is_active": True}])
    session.execute(insert(workspace_table), [{"id": 1, "organization_id": 1, "created_by_user_id": 1, "name": "My Workspace", "slug": "my-workspace", "workspace_type": "personal", "is_active": True}, {"id": 2, "organization_id": 2, "created_by_user_id": 2, "name": "Other Workspace", "slug": "other-workspace", "workspace_type": "personal", "is_active": True}, {"id": 3, "organization_id": 1, "created_by_user_id": 1, "name": "Second Workspace", "slug": "second-workspace", "workspace_type": "personal", "is_active": True}])
    report = {"executive_report": {"executive_summary": "Compare the offers.", "key_facts": ["Offer A is remote"], "derived_facts": ["$8,000 difference"], "alternatives": [{"option": "Offer A", "benefits": ["Remote"], "downsides": ["Limited promotion"]}], "recommended_move": "Choose based on verified growth path.", "confidence": {"level": "moderate"}, "unresolved_questions": ["How reliable is the management track?"], "provider_request": {"secret": "must not persist"}}}
    session.execute(insert(intelligence_session_table), [{"id": 1, "organization_id": 1, "workspace_id": 1, "created_by_user_id": 1, "title": "Job offers", "goal": "Which job should I take?", "session_type": "decision_analysis", "status": "completed", "is_active": True, "report_json": report}, {"id": 2, "organization_id": 1, "workspace_id": 3, "created_by_user_id": 1, "title": "Second", "goal": "Second scope", "session_type": "decision_analysis", "status": "completed", "is_active": True, "report_json": None}, {"id": 3, "organization_id": 2, "workspace_id": 2, "created_by_user_id": 2, "title": "Other", "goal": "Other scope", "session_type": "decision_analysis", "status": "completed", "is_active": True, "report_json": None}])
    session.commit()
    yield session
    session.close()
    engine.dispose()


def _create(db):
    result = personal_decision_service.create(db, user_id=1, organization_id=1, workspace_id=1, source_session_id=1, title="Career choice", decision_type="career_decision")
    db.commit()
    return result


def test_model_schema_and_curated_snapshot_exclude_provider_internals(db):
    decision = _create(db)
    assert {"user_id", "organization_id", "workspace_id", "analysis_snapshot_json", "outcome_status"} <= set(personal_decision_table.c.keys())
    assert decision["status"] == "open" and decision["outcome_status"] == "not_recorded"
    assert decision["recommendation"] == "Choose based on verified growth path."
    assert decision["analysis_snapshot_json"]["derived_facts"] == ["$8,000 difference"]
    assert "provider_request" not in decision["analysis_snapshot_json"]


def test_create_list_filters_get_and_tenant_hidden_source_scope(db):
    _create(db)
    assert len(personal_decision_service.repository.list_owned(db, user_id=1, organization_id=1, workspace_id=1, status="open", decision_type="career_decision")) == 1
    with pytest.raises(PersonalDecisionNotFoundError):
        personal_decision_service.create(db, user_id=1, organization_id=1, workspace_id=1, source_session_id=2, title=None, decision_type="general")
    with pytest.raises(PersonalDecisionNotFoundError):
        personal_decision_service.create(db, user_id=1, organization_id=1, workspace_id=1, source_session_id=3, title=None, decision_type="general")
    with pytest.raises(PersonalDecisionNotFoundError):
        personal_decision_service.repository.get_owned(db, decision_id=1, user_id=2, organization_id=2, workspace_id=2)


def test_choice_review_and_lifecycle_preserve_aura_recommendation(db):
    decision = _create(db)
    review = datetime(2026, 9, 1, tzinfo=timezone.utc)
    decided = personal_decision_service.update(db, decision_id=decision["id"], user_id=1, organization_id=1, workspace_id=1, changes={"user_choice": "Offer A", "user_choice_rationale": "Evenings matter", "review_date": review})
    assert decided["status"] == "decided" and decided["user_choice"] == "Offer A"
    assert decided["recommendation"] == "Choose based on verified growth path."
    assert decided["review_date"].replace(tzinfo=timezone.utc) == review
    waiting = personal_decision_service.update(db, decision_id=decision["id"], user_id=1, organization_id=1, workspace_id=1, changes={"status": "awaiting_outcome"})
    assert waiting["outcome_status"] == "pending"
    completed = personal_decision_service.update(db, decision_id=decision["id"], user_id=1, organization_id=1, workspace_id=1, changes={"status": "completed", "outcome_status": "recorded"})
    assert completed["status"] == "completed" and completed["outcome_status"] == "recorded"


def test_invalid_transition_and_delete_are_isolated(db):
    decision = _create(db)
    with pytest.raises(PersonalDecisionTransitionError):
        personal_decision_service.update(db, decision_id=decision["id"], user_id=1, organization_id=1, workspace_id=1, changes={"status": "awaiting_outcome"})
    personal_decision_service.delete(db, decision_id=decision["id"], user_id=1, organization_id=1, workspace_id=1)
    db.commit()
    assert db.execute(select(personal_decision_table)).mappings().all() == []
    assert db.execute(select(intelligence_session_table).where(intelligence_session_table.c.id == 1)).mappings().one()["is_active"] is True
