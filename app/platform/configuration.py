"""Single read model for installed Aura OS capabilities and tenant-safe defaults."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PlatformConfiguration:
    default_domain: str = "business"
    enabled_capabilities: frozenset[str] = field(default_factory=frozenset)

    def allows(self, capability: str) -> bool:
        return not self.enabled_capabilities or capability in self.enabled_capabilities
