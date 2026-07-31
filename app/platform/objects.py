"""Domain-neutral Aura OS organizational objects and lifecycle invariants."""

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


def _id() -> UUID: return uuid4()
def _now() -> datetime: return datetime.now(timezone.utc)


class Status(StrEnum):
    DRAFT = "draft"; ACTIVE = "active"; COMPLETED = "completed"; ARCHIVED = "archived"


class PlatformObject(BaseModel):
    id: UUID = Field(default_factory=_id)
    organization_id: int
    workspace_id: int | None = None
    domain: str = "business"
    object_type: str = "platform_object"
    status: Status = Status.DRAFT
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)
    created_by_user_id: int | None = None
    updated_by_user_id: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    tags: set[str] = Field(default_factory=set)
    labels: dict[str, str] = Field(default_factory=dict)
    custom_fields: dict[str, Any] = Field(default_factory=dict)
    permission_reference: str | None = None
    version: int = Field(default=1, ge=1)

    def activate(self):
        if self.status is Status.ARCHIVED: raise ValueError("Archived objects cannot be activated.")
        self.status, self.updated_at = Status.ACTIVE, _now()
        return self

    def revise(self, *, author_user_id: int | None = None, **changes):
        for field, value in changes.items():
            if field in {"id", "organization_id", "created_at", "created_by_user_id"}:
                raise ValueError(f"'{field}' is immutable.")
            setattr(self, field, value)
        self.updated_by_user_id, self.updated_at, self.version = author_user_id, _now(), self.version + 1
        return self

    def complete(self):
        if self.status is not Status.ACTIVE: raise ValueError("Only active objects can be completed.")
        self.status, self.updated_at = Status.COMPLETED, _now()
        return self


class KPI(BaseModel):
    name: str; target: float | str | None = None; current: float | str | None = None; unit: str | None = None


class Goal(PlatformObject):
    object_type: str = "goal"
    title: str; objective: str
    owner_user_id: int | None = None
    deadline: datetime | None = None
    kpis: list[KPI] = Field(default_factory=list)
    milestone_ids: list[UUID] = Field(default_factory=list)
    project_ids: list[UUID] = Field(default_factory=list)
    decision_ids: list[UUID] = Field(default_factory=list)


class Project(PlatformObject):
    object_type: str = "project"
    name: str; goal_id: UUID | None = None
    owner_user_id: int | None = None
    task_ids: list[UUID] = Field(default_factory=list)


class TaskPriority(StrEnum): LOW = "low"; MEDIUM = "medium"; HIGH = "high"; CRITICAL = "critical"

class Task(PlatformObject):
    object_type: str = "task"
    title: str; project_id: UUID | None = None; goal_id: UUID | None = None
    assignee_user_id: int | None = None; priority: TaskPriority = TaskPriority.MEDIUM
    deadline: datetime | None = None; dependency_ids: list[UUID] = Field(default_factory=list)


class Decision(PlatformObject):
    object_type: str = "decision"
    title: str; decision: str; reason: str
    confidence: int = Field(ge=0, le=100)
    evidence: list[str] = Field(default_factory=list)
    participant_user_ids: list[int] = Field(default_factory=list)
    goal_id: UUID | None = None; project_id: UUID | None = None
    outcome: str | None = None; lessons_learned: str | None = None


class TimelineEvent(PlatformObject):
    object_type: str = "timeline_event"
    event_type: str; title: str; related_object_id: UUID | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class KnowledgeDocument(PlatformObject):
    object_type: str = "knowledge_document"
    title: str; source_type: str; external_reference: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
