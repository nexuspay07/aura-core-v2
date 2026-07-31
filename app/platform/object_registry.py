"""Catalog of registered platform object types for discovery and plugins."""
from app.platform.objects import PlatformObject

class PlatformObjectRegistry:
    def __init__(self): self._types = {}
    def register(self, object_type: type[PlatformObject]) -> None:
        key = object_type.model_fields["object_type"].default
        if key in self._types: raise ValueError(f"Platform object '{key}' is already registered.")
        self._types[key] = object_type
    def manifest(self) -> list[dict]: return [{"key": key, "class": value.__name__} for key, value in sorted(self._types.items())]
