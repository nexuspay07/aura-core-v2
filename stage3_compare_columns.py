import app.main

from sqlalchemy import create_engine, inspect
from app.db.database import Base

DATABASE_URL = "sqlite:///K:/DEV/AURA/AURA_CORE_V2/aura_stage3_test.db"

engine = create_engine(DATABASE_URL)
inspector = inspect(engine)

errors = []

for table_name, orm_table in sorted(Base.metadata.tables.items()):
    if table_name not in inspector.get_table_names():
        errors.append(f"{table_name}: table missing from migrated database")
        continue

    database_columns = {
        column["name"]
        for column in inspector.get_columns(table_name)
    }
    orm_columns = set(orm_table.columns.keys())

    missing_from_database = sorted(orm_columns - database_columns)
    missing_from_orm = sorted(database_columns - orm_columns)

    if missing_from_database:
        errors.append(
            f"{table_name}: ORM columns missing from database: "
            f"{missing_from_database}"
        )

    if missing_from_orm:
        errors.append(
            f"{table_name}: database columns missing from ORM: "
            f"{missing_from_orm}"
        )

if errors:
    print("ORM/MIGRATION COLUMN COMPARISON: REVIEW REQUIRED")
    for error in errors:
        print(error)
    raise SystemExit(1)

print("ORM/MIGRATION COLUMN COMPARISON: PASSED")
