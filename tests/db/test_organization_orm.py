import importlib

import pytest
from sqlalchemy import create_engine, event, insert, select, update
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.db.organization_orm import Organization
from app.db.organization_table import organization_table
from app.db.user_table import user_table


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    event.listen(engine, "connect", lambda dbapi, _: dbapi.execute("PRAGMA foreign_keys=ON"))
    Base.metadata.create_all(engine, tables=[user_table, organization_table])
    test_session = sessionmaker(bind=engine)()
    test_session.execute(
        insert(user_table),
        [
            {"id": 1, "email": "owner-one@example.test", "password_hash": "test"},
            {"id": 2, "email": "owner-two@example.test", "password_hash": "test"},
        ],
    )
    test_session.commit()
    yield test_session
    test_session.close()
    engine.dispose()


def test_organization_mapper_reuses_the_canonical_core_table():
    assert Organization.__table__ is organization_table
    assert organization_table.metadata is Base.metadata
    assert list(Base.metadata.tables).count("organizations") == 1


def test_orm_and_core_interoperate_on_the_same_row(session):
    orm_organization = Organization(
        name="ORM Organization",
        slug="orm-organization",
        owner_user_id=1,
        plan="free",
        subscription_status="inactive",
        is_active=True,
    )
    session.add(orm_organization)
    session.commit()

    assert session.execute(
        select(organization_table.c.name).where(organization_table.c.id == orm_organization.id)
    ).scalar_one() == "ORM Organization"

    core_organization_id = session.execute(
        insert(organization_table).values(
            name="Core Organization",
            slug="core-organization",
            owner_user_id=2,
            plan="free",
            subscription_status="inactive",
            is_active=True,
        )
    ).inserted_primary_key[0]
    session.commit()
    assert session.get(Organization, core_organization_id).name == "Core Organization"

    session.execute(
        update(organization_table)
        .where(organization_table.c.id == orm_organization.id)
        .values(name="Updated by Core")
    )
    session.commit()
    session.expire(orm_organization)
    assert orm_organization.name == "Updated by Core"

    session.delete(orm_organization)
    session.commit()
    assert session.execute(
        select(organization_table.c.id).where(organization_table.c.id == orm_organization.id)
    ).first() is None


def test_existing_organization_constraints_remain_enforced(session):
    session.add(
        Organization(
            name="Canonical",
            slug="canonical",
            owner_user_id=1,
            plan="free",
            subscription_status="inactive",
            is_active=True,
        )
    )
    session.commit()

    session.add(
        Organization(
            name="Duplicate Slug",
            slug="canonical",
            owner_user_id=1,
            plan="free",
            subscription_status="inactive",
            is_active=True,
        )
    )
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()

    session.add(
        Organization(
            name="Unknown Owner",
            slug="unknown-owner",
            owner_user_id=999,
            plan="free",
            subscription_status="inactive",
            is_active=True,
        )
    )
    # SQLite reports this foreign-key violation as OperationalError.
    with pytest.raises(OperationalError):
        session.commit()
    session.rollback()


def test_organization_mapper_import_is_idempotent_and_schema_neutral():
    module = importlib.import_module("app.db.organization_orm")
    assert module.Organization.__table__ is organization_table
    assert list(Base.metadata.tables).count("organizations") == 1
