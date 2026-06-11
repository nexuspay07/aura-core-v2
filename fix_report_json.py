from sqlalchemy import create_engine, text

engine = create_engine(
    "sqlite:///./aura.db"
)

with engine.connect() as conn:

    conn.execute(
        text(
            """
            ALTER TABLE intelligence_sessions
            ADD COLUMN report_json TEXT
            """
        )
    )

    conn.commit()

print(
    "report_json column added successfully"
)