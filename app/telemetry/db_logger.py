from app.db.database import SessionLocal
from app.db.models import UsageLog


def log_usage(tenant_id, domain, message, response):
    """
    Saves telemetry usage log to database
    """

    db = SessionLocal()

    try:

        log = UsageLog(
            tenant_id=tenant_id,
            domain=domain,
            message=message,
            response=response
        )

        db.add(log)

        db.commit()

    finally:
        db.close()
