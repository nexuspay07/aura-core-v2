from app.core.intelligence.base_models import (
    IntelligenceResult,
)


class StrategicSimulationResult(
    IntelligenceResult
):

    best_strategy: str

    confidence: float

    reasoning: list[str]

    tradeoffs: list[str]