from app.platform.bootstrap import platform_registry


class DomainRegistry:

    @classmethod
    def get(cls, domain_name: str):
        """Backward-compatible facade over the Aura OS installed-domain registry."""
        return platform_registry.get_domain(domain_name)
