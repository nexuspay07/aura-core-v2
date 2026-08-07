from sqlalchemy import create_engine, event, insert, select, update
from sqlalchemy.orm import sessionmaker

from app.db.business_profile_table import business_profile_table
from app.db.database import metadata
from app.db.organization_member_table import organization_member_table
from app.db.organization_table import organization_table
from app.db.user_table import user_table
from app.db.workspace_member_table import workspace_member_table
from app.db.workspace_table import workspace_table
from app.services.identity_service import identity_service
from app.services.onboarding_service import onboarding_service


def _session():
    engine = create_engine("sqlite://")
    event.listen(engine, "connect", lambda connection, _: connection.execute("PRAGMA foreign_keys=ON"))
    metadata.create_all(engine)
    return sessionmaker(bind=engine)(), engine


def _user(db, user_id=1):
    db.execute(insert(user_table).values(id=user_id, email=f"user{user_id}@test.local", password_hash="x"))


def test_personal_onboarding_creates_truthful_profile_less_context():
    db, engine = _session()
    try:
        _user(db)
        result = onboarding_service.initialize(db, 1, "Alex", account_type="personal")
        db.commit()
        organization = db.execute(select(organization_table).where(organization_table.c.id == result["organization_id"])).mappings().one()
        workspace = db.execute(select(workspace_table).where(workspace_table.c.id == result["workspace_id"])).mappings().one()
        user = db.execute(select(user_table).where(user_table.c.id == 1)).mappings().one()
        assert organization["name"] == "Personal Space" and organization["account_type"] == "personal"
        assert workspace["name"] == "My Workspace" and workspace["workspace_type"] == "personal"
        assert user["active_workspace_id"] == workspace["id"]
        assert db.execute(select(business_profile_table).where(business_profile_table.c.workspace_id == workspace["id"])).first() is None
        identity = identity_service.resolve(db, 1)
        assert identity["organization"]["id"] == organization["id"] and identity["workspace"]["id"] == workspace["id"]
    finally:
        db.close(); engine.dispose()


def test_business_and_enterprise_onboarding_persist_requested_details_and_profile():
    db, engine = _session()
    try:
        for user_id, account_type in ((1, "business"), (2, "enterprise")):
            _user(db, user_id)
            result = onboarding_service.initialize(
                db, user_id, "Owner", account_type=account_type,
                organization_name=f"{account_type.title()} Co", industry="technology",
                company_size="11-50", workspace_name="Leadership",
            )
            organization = db.execute(select(organization_table).where(organization_table.c.id == result["organization_id"])).mappings().one()
            workspace = db.execute(select(workspace_table).where(workspace_table.c.id == result["workspace_id"])).mappings().one()
            assert organization["account_type"] == account_type and organization["industry"] == "technology"
            assert workspace["name"] == "Leadership"
            assert db.execute(select(business_profile_table).where(business_profile_table.c.workspace_id == workspace["id"])).first()
        db.commit()
    finally:
        db.close(); engine.dispose()


def test_invalid_active_workspace_falls_back_deterministically_and_derives_organization():
    db, engine = _session()
    try:
        _user(db)
        for organization_id, workspace_id in ((1, 10), (2, 20)):
            db.execute(insert(organization_table).values(id=organization_id, name=f"Org {organization_id}", slug=f"org-{organization_id}", owner_user_id=1, plan="free", subscription_status="inactive", account_type="business", is_active=True))
            db.execute(insert(workspace_table).values(id=workspace_id, organization_id=organization_id, created_by_user_id=1, name=f"Space {workspace_id}", slug=f"space-{workspace_id}", workspace_type="business", is_active=True))
            db.execute(insert(organization_member_table).values(organization_id=organization_id, user_id=1, role="owner", status="active", is_active=True))
            db.execute(insert(workspace_member_table).values(workspace_id=workspace_id, user_id=1, role="owner", status="active", is_active=True))
        # A once-valid workspace becomes inaccessible.  The earliest remaining
        # active membership determines the deterministic fallback.
        db.execute(update(user_table).where(user_table.c.id == 1).values(active_workspace_id=20))
        db.execute(update(workspace_member_table).where(workspace_member_table.c.workspace_id == 20).values(is_active=False))
        db.commit()
        identity = identity_service.resolve(db, 1)
        db.commit()
        assert identity["workspace"]["id"] == 10
        assert identity["organization"]["id"] == 1
        assert db.execute(select(user_table.c.active_workspace_id).where(user_table.c.id == 1)).scalar_one() == 10
    finally:
        db.close(); engine.dispose()


def test_no_accessible_workspace_clears_context_and_requires_onboarding():
    db, engine = _session()
    try:
        _user(db)
        db.execute(update(user_table).where(user_table.c.id == 1).values(active_workspace_id=None))
        db.commit()
        identity = identity_service.resolve(db, 1)
        db.commit()
        assert identity["onboarding_required"] is True
        assert identity["organization"] is None and identity["workspace"] is None
        assert db.execute(select(user_table.c.active_workspace_id).where(user_table.c.id == 1)).scalar_one() is None
    finally:
        db.close(); engine.dispose()
