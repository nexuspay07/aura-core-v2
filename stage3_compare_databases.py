from sqlalchemy import create_engine, inspect

EXISTING_URL = "sqlite:///K:/DEV/AURA/AURA_CORE_V2/aura.db"
FRESH_URL = "sqlite:///K:/DEV/AURA/AURA_CORE_V2/aura_stage3_test.db"

existing_engine = create_engine(EXISTING_URL)
fresh_engine = create_engine(FRESH_URL)

existing_tables = set(inspect(existing_engine).get_table_names())
fresh_tables = set(inspect(fresh_engine).get_table_names())

existing_only = sorted(existing_tables - fresh_tables)
fresh_only = sorted(fresh_tables - existing_tables)
shared = sorted(existing_tables & fresh_tables)

print(f"EXISTING TABLE COUNT: {len(existing_tables)}")
print(f"FRESH TABLE COUNT: {len(fresh_tables)}")
print(f"SHARED TABLE COUNT: {len(shared)}")

print("")
print(f"ONLY IN EXISTING DATABASE: {len(existing_only)}")
for table in existing_only:
    print(f"  - {table}")

print("")
print(f"ONLY IN FRESH DATABASE: {len(fresh_only)}")
for table in fresh_only:
    print(f"  - {table}")

if existing_only or fresh_only:
    print("")
    print("DATABASE TABLE COMPARISON: DIFFERENCES FOUND")
else:
    print("")
    print("DATABASE TABLE COMPARISON: PASSED")
