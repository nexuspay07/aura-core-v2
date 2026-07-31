"""Versioned extension contracts shared by Aura OS capabilities."""

from abc import ABC
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, Field


class NavigationItem(BaseModel):
    key: str
    label: str
    path: str
    icon: str | None = None


class DomainManifest(BaseModel):
    key: str
    name: str
    version: str = "1.0"
    capabilities: set[str] = Field(default_factory=set)
    navigation: list[NavigationItem] = Field(default_factory=list)


class IndustryManifest(BaseModel):
    key: str
    name: str
    domain_key: str
    version: str = "1.0"
    settings: dict[str, Any] = Field(default_factory=dict)


class PluginManifest(BaseModel):
    key: str
    name: str
    version: str
    provides: set[str] = Field(default_factory=set)
    requires: set[str] = Field(default_factory=set)


class AgentManifest(BaseModel):
    key: str
    name: str
    version: str
    capabilities: set[str] = Field(default_factory=set)


class ExternalProviderManifest(BaseModel):
    key: str
    name: str
    version: str
    data_types: set[str] = Field(default_factory=set)


class MarketplacePackageManifest(BaseModel):
    key: str
    name: str
    version: str
    package_type: str
    provides: set[str] = Field(default_factory=set)


class DomainExtension(ABC):
    """Minimal executable contract for a domain; no framework dependencies."""

    manifest: DomainManifest

    def build_context(self, *, goal: str, context: dict[str, Any]) -> dict[str, Any]:
        return context


DomainFactory = Callable[[], DomainExtension]
