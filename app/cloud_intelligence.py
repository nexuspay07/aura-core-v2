from sqlalchemy.orm import Session

from app.core.cognitive_loop import cognitive_loop


async def cloud_intelligence(
    db: Session,
    tenant_id: str,
    domain: str,
    message: str
):
    """
    Legacy compatibility wrapper.

    Old engine-based orchestration has been replaced
    by the centralized cognitive loop pipeline.
    """

    scenario = {
        "goal": message,
        "risk_tolerance": 0.5,
        "budget": 10000,
        "market": "normal"
    }

    profile = {
        "tenant_id": tenant_id,
        "domain": domain
    }

    result = cognitive_loop.run_intelligence_pipeline(
        message,
        scenario,
        profile
    )

    return {
        "status": "success",
        "tenant_id": tenant_id,
        "domain": domain,
        "response": result
    }