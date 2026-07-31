"""Agent lifecycle and permission contract. No agent intelligence is implemented here."""

from abc import ABC, abstractmethod
from enum import StrEnum
from app.platform.contracts import AgentManifest


class AgentState(StrEnum): CREATED = "created"; ACTIVE = "active"; SUSPENDED = "suspended"; RETIRED = "retired"


class Agent(ABC):
    manifest: AgentManifest

    @abstractmethod
    def authorize(self, permissions: set[str]) -> bool: ...

    @abstractmethod
    def handle(self, message: dict) -> dict: ...
