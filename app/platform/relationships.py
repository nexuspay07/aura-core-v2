"""Generic graph edge contract between any two Aura OS objects."""
from enum import StrEnum
from uuid import UUID
from pydantic import BaseModel

class RelationshipType(StrEnum):
    PARENT = "parent"; CHILD = "child"; DEPENDENCY = "dependency"; REFERENCE = "reference"; ASSOCIATION = "association"; RELATED = "related"

class ObjectRelationship(BaseModel):
    source_id: UUID; target_id: UUID; relationship_type: RelationshipType
    organization_id: int; metadata: dict = {}
