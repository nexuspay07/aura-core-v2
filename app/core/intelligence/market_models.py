from pydantic import BaseModel

from app.core.intelligence.base_models import (
    IntelligenceMetric,
    IntelligenceResult,
)


class MarketIntelligenceResult(IntelligenceResult):

    opportunity: IntelligenceMetric

    threat: IntelligenceMetric

    competition: IntelligenceMetric