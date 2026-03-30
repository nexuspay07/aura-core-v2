from AURA.AURA_CORE_V2.app.db.database import SessionLocal
from app.db.models import UsageLog


def get_all_usage_logs():
    """
    Returns all telemetry logs from the database
    """

    db = SessionLocal()

    try:

        logs = db.query(UsageLog).all()

        results = []

        for log in logs:
            results.append({
                "id": log.id,
                "tenant_id": log.tenant_id,
                "domain": log.domain,
                "message": log.message,
                "response": log.response,
                "timestamp": str(log.timestamp)
            })

        return results

    finally:
        db.close()
