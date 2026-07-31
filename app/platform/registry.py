"""Thread-safe, deterministic registry for Aura OS installed capabilities."""

from threading import RLock

from app.platform.contracts import DomainExtension, DomainFactory, DomainManifest, IndustryManifest, PluginManifest


class PlatformRegistry:
    def __init__(self) -> None:
        self._lock = RLock()
        self._domains: dict[str, DomainFactory] = {}
        self._industries: dict[str, IndustryManifest] = {}
        self._plugins: dict[str, PluginManifest] = {}

    def register_domain(self, factory: DomainFactory) -> None:
        extension = factory()
        key = extension.manifest.key
        with self._lock:
            if key in self._domains:
                raise ValueError(f"Domain '{key}' is already registered.")
            self._domains[key] = factory

    def get_domain(self, key: str) -> DomainExtension:
        with self._lock:
            factory = self._domains.get(key)
        if factory is None:
            raise ValueError(f"Unsupported domain: {key}")
        return factory()

    def register_industry(self, manifest: IndustryManifest) -> None:
        with self._lock:
            if manifest.domain_key not in self._domains:
                raise ValueError(f"Industry '{manifest.key}' requires uninstalled domain '{manifest.domain_key}'.")
            if manifest.key in self._industries:
                raise ValueError(f"Industry '{manifest.key}' is already registered.")
            self._industries[manifest.key] = manifest

    def register_plugin(self, manifest: PluginManifest) -> None:
        with self._lock:
            missing = manifest.requires - self.available_capabilities()
            if missing:
                raise ValueError(f"Plugin '{manifest.key}' requires unavailable capabilities: {sorted(missing)}")
            if manifest.key in self._plugins:
                raise ValueError(f"Plugin '{manifest.key}' is already registered.")
            self._plugins[manifest.key] = manifest

    def available_capabilities(self) -> set[str]:
        with self._lock:
            capabilities = set().union(*(self.get_domain(key).manifest.capabilities for key in self._domains)) if self._domains else set()
            for plugin in self._plugins.values():
                capabilities.update(plugin.provides)
            return capabilities

    def manifest(self) -> dict:
        with self._lock:
            return {
                "domains": [self.get_domain(key).manifest.model_dump(mode="json") for key in sorted(self._domains)],
                "industries": [manifest.model_dump(mode="json") for _, manifest in sorted(self._industries.items())],
                "plugins": [manifest.model_dump(mode="json") for _, manifest in sorted(self._plugins.items())],
            }
