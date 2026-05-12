from sqlalchemy import Table, Column, Integer, String, Float, DateTime, Text
from datetime import datetime, timezone

from app.db.database import metadata


decision_memory_table = Table(
    "decision_memory",
    metadata,

    Column("id", Integer, primary_key=True),
    Column("session_id", String, index=True, nullable=False),
    Column("timestamp", DateTime, default=lambda: datetime.now(timezone.utc)),

    Column("goal", Text),
    Column("business_model", String),
    Column("business_stage", String),
    Column("market", String),
    Column("competition_pressure", String),
    Column("trust_dependency", String),
    Column("scalability", String),

    Column("recommended_strategy", String),
    Column("risk", String),
    Column("decision_score", Float),
    Column("failure_probability", Float),

    Column("current_bottleneck", Text),
    Column("growth_blocker", Text),
    Column("strategic_warning", Text),

    Column("prediction_confidence", Float),
    Column("growth_probability", String),
    Column("failure_probability_label", String),

    Column("recommended_move", Text),
)