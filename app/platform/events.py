"""Domain-neutral lifecycle event contracts."""
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

class PlatformEvent(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    event_type: str
    object_id: UUID
    object_type: str
    organization_id: int
    actor_user_id: int | None = None
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    payload: dict[str, Any] = Field(default_factory=dict)

class EventPublisher:
    def publish(self, event: PlatformEvent) -> None: ...
