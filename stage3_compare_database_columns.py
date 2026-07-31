from sqlalchemy import create_engine, inspect

EXISTING_URL = "sqlite:///K:/DEV/AURA/AURA_CORE_V2/aura.db"
FRESH_URL = "sqlite:///K:/DEV/AURA/AURA_CORE_V2/aura_stage3_test.db"

existing_inspector = inspect(create_engine(EXISTING_URL))
fresh_inspector = inspect(create_engine(FRESH_URL))

existing_tables = set(existing_inspector.get_table_names())
fresh_tables = set(fresh_inspector.get_table_names())

shared_tables = sorted(
    (existing_tables & fresh_tables) - {"alembic_version"}
)

differences = []

for table in shared_tables:
    existing_columns = {
        column["name"]: {
            "type": str(column["type"]),
            "nullable": column.get("nullable"),
            "default": str(column.get("default")),
            "primary_key": column.get("primary_key"),
        }
        for column in existing_inspector.get_columns(table)
    }

    fresh_columns = {
        column["name"]: {
            "type": str(column["type"]),
            "nullable": column.get("nullable"),
            "default": str(column.get("default")),
            "primary_key": column.get("primary_key"),
        }
        for column in fresh_inspector.get_columns(table)
    }

    if existing_columns != fresh_columns:
        differences.append(table)

        print("=" * 80)
        print(f"SCHEMA DIFFERENCE: {table}")
        print("=" * 80)

        existing_only = sorted(
            set(existing_columns) - set(fresh_columns)
        )
        fresh_only = sorted(
            set(fresh_columns) - set(existing_columns)
        )

        if existing_only:
            print("Columns only in existing database:")
            for column in existing_only:
                print(f"  - {column}")

        if fresh_only:
            print("Columns only in fresh database:")
            for column in fresh_only:
                print(f"  - {column}")

        shared_columns = sorted(
            set(existing_columns) & set(fresh_columns)
        )

        for column in shared_columns:
            if existing_columns[column] != fresh_columns[column]:
                print(f"Column differs: {column}")
                print(f"  Existing: {existing_columns[column]}")
                print(f"  Fresh:    {fresh_columns[column]}")

if differences:
    print("")
    print(f"TABLES WITH SCHEMA DIFFERENCES: {len(differences)}")
    for table in differences:
        print(f"  - {table}")
    raise SystemExit(1)

print("EXISTING/FRESH COLUMN COMPARISON: PASSED")
