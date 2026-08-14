from sqlalchemy import create_engine, event, insert
from sqlalchemy.orm import sessionmaker

from app.db.database import metadata
from app.db.organization_member_table import organization_member_table
from app.db.organization_table import organization_table
from app.db.user_table import user_table
from app.db.workspace_member_table import workspace_member_table
from app.db.workspace_table import workspace_table
from app.services.identity_service import identity_service
from app.services.product_capabilities import resolve_product_capabilities


def _session():
    engine = create_engine("sqlite://")
    event.listen(engine, "connect", lambda connection, _: connection.execute("PRAGMA foreign_keys=ON"))
    metadata.create_all(engine)
    return sessionmaker(bind=engine)(), engine


def _identity_for_account_type(db, account_type):
    db.execute(insert(user_table).values(id=1, email="person@test.local", password_hash="x"))
    db.execute(insert(organization_table).values(id=1, name="Context", slug=f"{account_type}-context", owner_user_id=1, account_type=account_type, plan="free", subscription_status="inactive", is_active=True))
    db.execute(insert(workspace_table).values(id=1, organization_id=1, created_by_user_id=1, name="My Workspace", slug=f"{account_type}-workspace", workspace_type=account_type, is_active=True))
    db.execute(insert(organization_member_table).values(organization_id=1, user_id=1, role="owner", status="active", is_active=True))
    db.execute(insert(workspace_member_table).values(workspace_id=1, user_id=1, role="owner", status="active", is_active=True))
    db.execute(user_table.update().where(user_table.c.id == 1).values(active_workspace_id=1))
    db.commit()
    return identity_service.resolve(db, 1)


def test_personal_capabilities_enable_personal_product_without_business_surfaces():
    policy = resolve_product_capabilities("personal")
    assert policy.product_mode == "personal"
    assert {"personal_home", "ask_aura", "decisions", "goals", "actions", "personal_context", "documents"} <= set(policy.capabilities)
    assert not {"organizations", "workspaces", "members", "marketplace", "simulations", "billing", "business_settings"} & set(policy.capabilities)


def test_business_and_enterprise_capabilities_preserve_existing_product_surfaces():
    business = resolve_product_capabilities("business")
    enterprise = resolve_product_capabilities("enterprise")
    business_surfaces = {"organizations", "workspaces", "members", "marketplace", "simulations", "billing", "business_settings"}
    assert business_surfaces <= set(business.capabilities)
    assert business_surfaces <= set(enterprise.capabilities)
    assert "enterprise_settings" not in business.capabilities
    assert "enterprise_settings" in enterprise.capabilities


def test_identity_derives_capabilities_from_persisted_organization_account_type():
    db, engine = _session()
    try:
        identity = _identity_for_account_type(db, "personal")
        assert identity["product_mode"] == "personal"
        assert "personal_home" in identity["capabilities"]
        assert "billing" not in identity["capabilities"]
    finally:
        db.close()
        engine.dispose()
