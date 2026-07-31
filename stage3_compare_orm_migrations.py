import app.main

from sqlalchemy import create_engine, inspect
from app.db.database import Base

DATABASE_URL = "sqlite:///K:/DEV/AURA/AURA_CORE_V2/aura_stage3_test.db"

engine = create_engine(DATABASE_URL)
inspector = inspect(engine)

database_tables = set(inspector.get_table_names())
database_tables.discard("alembic_version")

orm_tables = set(Base.metadata.tables.keys())

missing_from_database = sorted(orm_tables - database_tables)
missing_from_orm = sorted(database_tables - orm_tables)

print(f"ORM TABLE COUNT: {len(orm_tables)}")
print(f"MIGRATED TABLE COUNT: {len(database_tables)}")

print("")
print(f"ORM TABLES MISSING FROM DATABASE: {len(missing_from_database)}")
for table in missing_from_database:
    print(f"  - {table}")

print("")
print(f"DATABASE TABLES MISSING FROM ORM: {len(missing_from_orm)}")
for table in missing_from_orm:
    print(f"  - {table}")

if missing_from_database or missing_from_orm:
    print("")
    print("ORM/MIGRATION TABLE COMPARISON: REVIEW REQUIRED")
    raise SystemExit(1)

print("")
print("ORM/MIGRATION TABLE COMPARISON: PASSED")
