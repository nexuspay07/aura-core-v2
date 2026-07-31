from sqlalchemy import insert, select
from sqlalchemy.orm import Session

from app.db.usage_log_table import usage_log_table


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