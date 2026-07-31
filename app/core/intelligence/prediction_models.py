from pydantic import BaseModel

from app.core.intelligence.base_models import (
    IntelligenceMetric,
    IntelligenceResult,
)


class PredictionResult(IntelligenceResult):

    confidence: IntelligenceMetric

    success_probability: IntelligenceMetric

    execution_risk: IntelligenceMetric

    expected_outcome: str

    assumptions: list[str]