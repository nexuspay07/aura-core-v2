"""Reusable workflow contracts; execution is supplied by installed workflow packs."""

from abc import ABC, abstractmethod
from pydantic import BaseModel, Field


class WorkflowDefinition(BaseModel):
    key: str; name: str; version: str = "1.0"
    triggers: set[str] = Field(default_factory=set)
    steps: list[str] = Field(default_factory=list)


class WorkflowRunner(ABC):
    @abstractmethod
    def run(self, definition: WorkflowDefinition, context: dict) -> dict: ...
