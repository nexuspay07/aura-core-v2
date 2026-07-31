from sqlalchemy import create_engine, inspect

DATABASE_URL = "sqlite:///K:/DEV/AURA/AURA_CORE_V2/aura_stage3_test.db"

engine = create_engine(DATABASE_URL)
inspector = inspect(engine)

tables = set(inspector.get_table_names())
errors = []

for table in sorted(tables):
    for foreign_key in inspector.get_foreign_keys(table):
        target_table = foreign_key.get("referred_table")
        target_columns = foreign_key.get("referred_columns") or []

        if target_table not in tables:
            errors.append(
                f"{table}: foreign key points to missing table {target_table}"
            )
            continue

        existing_target_columns = {
            column["name"]
            for column in inspector.get_columns(target_table)
        }

        for target_column in target_columns:
            if target_column not in existing_target_columns:
                errors.append(
                    f"{table}: foreign key points to missing column "
                    f"{target_table}.{target_column}"
                )

if errors:
    print("FOREIGN KEY TARGET VALIDATION: FAILED")
    for error in errors:
        print(error)
    raise SystemExit(1)

print("FOREIGN KEY TARGET VALIDATION: PASSED")
