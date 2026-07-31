from typing import Any

from pydantic import BaseModel


class EngineResult(BaseModel):

    engine: str

    version: str = "2.0"

    metrics: dict[str, Any] = {}

    findings: list[Any] = []

    reasoning: list[str] = []

    recommendations: list[str] = []

    metadata: dict[str, Any] = {}