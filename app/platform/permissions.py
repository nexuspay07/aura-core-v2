"""Object-level permission contract shared across all platform objects."""
from enum import StrEnum
from uuid import UUID
from pydantic import BaseModel

class ObjectRole(StrEnum): OWNER = "owner"; EDITOR = "editor"; VIEWER = "viewer"; ADMINISTRATOR = "administrator"
class ObjectPermission(BaseModel):
    object_id: UUID; principal_id: str; role: ObjectRole; organization_id: int
