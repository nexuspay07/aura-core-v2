from pathlib import Path

from sqlalchemy import create_engine, inspect

DATABASE_URL = "sqlite:///K:/DEV/AURA/AURA_CORE_V2/aura_stage3_test.db"
REPORT_PATH = Path("stage3_fresh_schema_report.txt")

engine = create_engine(DATABASE_URL)
inspector = inspect(engine)

tables = sorted(inspector.get_table_names())

lines = []
lines.append(f"DATABASE URL: {DATABASE_URL}")
lines.append(f"TABLE COUNT: {len(tables)}")
lines.append("")

for table in tables:
    lines.append("=" * 80)
    lines.append(f"TABLE: {table}")
    lines.append("=" * 80)

    columns = inspector.get_columns(table)
    lines.append("COLUMNS:")
    for column in columns:
        lines.append(
            f"  - {column['name']} | "
            f"type={column['type']} | "
            f"nullable={column.get('nullable')} | "
            f"default={column.get('default')} | "
            f"primary_key={column.get('primary_key')}"
        )

    primary_key = inspector.get_pk_constraint(table)
    lines.append(f"PRIMARY KEY: {primary_key}")

    foreign_keys = inspector.get_foreign_keys(table)
    lines.append(f"FOREIGN KEYS ({len(foreign_keys)}):")
    for foreign_key in foreign_keys:
        lines.append(f"  - {foreign_key}")

    unique_constraints = inspector.get_unique_constraints(table)
    lines.append(f"UNIQUE CONSTRAINTS ({len(unique_constraints)}):")
    for constraint in unique_constraints:
        lines.append(f"  - {constraint}")

    check_constraints = inspector.get_check_constraints(table)
    lines.append(f"CHECK CONSTRAINTS ({len(check_constraints)}):")
    for constraint in check_constraints:
        lines.append(f"  - {constraint}")

    indexes = inspector.get_indexes(table)
    lines.append(f"INDEXES ({len(indexes)}):")
    for index in indexes:
        lines.append(f"  - {index}")

    lines.append("")

REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")

print(f"SCHEMA REPORT CREATED: {REPORT_PATH.resolve()}")
print(f"TABLE COUNT: {len(tables)}")
