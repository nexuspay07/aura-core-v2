from sqlalchemy.orm import Session

from app.services.telemetry_service import telemetry_service


def log_usage(
    db: Session,
    tenant_id: str = None,
    domain: str = None,
    message: str = None,
    response: str = None,
    organization_id: int = None,
    workspace_id: int = None,
    user_id: int = None,
    success: bool = True,
    latency_ms: int = None,
    model: str = None,
    tokens_used: int = None,
):
    """
    Legacy compatibility wrapper.

    Existing code can continue calling log_usage(),
    while all telemetry is delegated to the centralized
    TelemetryService.
    """

    telemetry_service.log_usage(
        db=db,
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