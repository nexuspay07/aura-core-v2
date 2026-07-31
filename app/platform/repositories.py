"""Persistence-agnostic contracts for future database or event-store adapters."""
from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from uuid import UUID
from app.platform.objects import PlatformObject

T = TypeVar("T", bound=PlatformObject)
class PlatformRepository(ABC, Generic[T]):
    @abstractmethod
    def get(self, object_id: UUID) -> T | None: ...
    @abstractmethod
    def save(self, object: T) -> T: ...
    @abstractmethod
    def delete(self, object_id: UUID) -> None: ...
    @abstractmethod
    def query(self, *, organization_id: int, domain: str | None = None, tags: set[str] | None = None) -> list[T]: ...

class GoalRepository(PlatformRepository): pass
class ProjectRepository(PlatformRepository): pass
class TaskRepository(PlatformRepository): pass
class DecisionRepository(PlatformRepository): pass
class TimelineRepository(PlatformRepository): pass
class KnowledgeRepository(PlatformRepository): pass
