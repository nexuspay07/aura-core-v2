from typing import Literal
from pydantic import BaseModel, ConfigDict
from sqlalchemy import insert, select
from sqlalchemy.orm import Session

from app.db.usage_log_table import usage_log_table


class IntelligenceExecutionTelemetry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: str
    user_id: int
    organization_id: int
    workspace_id: int
    route: str
    request_mode: str | None = None
    outcome: Literal["success", "partial", "failure", "clarification", "safety"]
    error_category: str | None = None
    provider: str | None = None
    model: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    reasoning_tokens: int | None = None
    total_tokens: int | None = None
    latency_ms: int
    provider_latency_ms: int | None = None
    retry_count: int | None = None
    provider_call_count: int | None = None
    session_id: int | None = None


class TelemetryService:
    """
    Centralized telemetry service.

    Responsible for:

    • Usage logging
    • Analytics
    • Audit history
    • Future KPI collection
    """

    @staticmethod
    def record_intelligence_execution(db: Session, event: IntelligenceExecutionTelemetry) -> None:
        values = event.model_dump()
        values["tokens_used"] = values.pop("total_tokens")
        values.update(message=None, response=None, success=event.outcome in {"success", "clarification", "safety"})
        db.execute(insert(usage_log_table).values(**values))
        db.commit()

    @staticmethod
    def log_usage(
        db: Session,
        *,
        tenant_id: str = None,
        organization_id: int = None,
        workspace_id: int = None,
        user_id: int = None,
        domain: str = None,
        message: str = None,
        response: str = None,
        success: bool = True,
        latency_ms: int = None,
        model: str = None,
        tokens_used: int = None,
    ):

        stmt = insert(usage_log_table).values(

            tenant_id=tenant_id,

            organization_id=organization_id,

            workspace_id=workspace_id,

            user_id=user_id,

            domain=domain,

            message=message,

            response=response,

            success=success,

            latency_ms=latency_ms,

            model=model,

            tokens_used=tokens_used,
        )

        db.execute(stmt)
        db.commit()

    @staticmethod
    def get_logs(
        db: Session,
        limit: int = 100,
    ):

        stmt = (
            select(usage_log_table)
            .order_by(usage_log_table.c.created_at.desc())
            .limit(limit)
        )

        rows = db.execute(stmt).mappings().all()

        return [dict(row) for row in rows]


telemetry_service = TelemetryService()
