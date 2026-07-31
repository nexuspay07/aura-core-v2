"""Registries for optional Aura OS capabilities that are not platform engines."""

from threading import RLock

from app.platform.contracts import AgentManifest, ExternalProviderManifest, MarketplacePackageManifest


class ManifestRegistry:
    def __init__(self, label: str) -> None:
        self.label, self._items, self._lock = label, {}, RLock()

    def register(self, manifest) -> None:
        with self._lock:
            if manifest.key in self._items:
                raise ValueError(f"Duplicate {self.label} '{manifest.key}'.")
            self._items[manifest.key] = manifest

    def list(self) -> list[dict]:
        with self._lock:
            return [item.model_dump(mode="json") for _, item in sorted(self._items.items())]


class ExtensionCatalog:
    def __init__(self) -> None:
        self.agents = ManifestRegistry("agent")
        self.external_providers = ManifestRegistry("external provider")
        self.marketplace_packages = ManifestRegistry("marketplace package")

    def manifest(self) -> dict:
        return {"agents": self.agents.list(), "external_providers": self.external_providers.list(), "marketplace_packages": self.marketplace_packages.list()}
