"""Common indexing projection for future platform-wide search adapters."""
from abc import ABC, abstractmethod
from pydantic import BaseModel
from app.platform.objects import PlatformObject

class SearchDocument(BaseModel):
    object_id: str; object_type: str; organization_id: int; domain: str; text: str; tags: list[str] = []
    @classmethod
    def from_object(cls, object: PlatformObject) -> "SearchDocument":
        return cls(object_id=str(object.id), object_type=object.object_type, organization_id=object.organization_id, domain=object.domain, text=" ".join(str(value) for value in object.model_dump().values() if isinstance(value, (str, int, float))), tags=sorted(object.tags))
class SearchIndex(ABC):
    @abstractmethod
    def index(self, document: SearchDocument) -> None: ...
