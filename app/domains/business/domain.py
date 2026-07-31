"""Business is Aura OS's first complete installed domain."""

from app.domains.business.business_domain_engine import business_domain_engine
from app.platform.contracts import DomainExtension, DomainManifest, NavigationItem


class BusinessDomain(DomainExtension):
    manifest = DomainManifest(
        key="business",
        name="Business",
        capabilities={"context", "executive_intelligence", "simulation", "reports", "kpis", "dashboard"},
        navigation=[NavigationItem(key="executive-intelligence", label="Executive Intelligence", path="/intelligence")],
    )

    def build_context(self, *, goal: str, context: dict) -> dict:
        subdomain = business_domain_engine.detect_subdomain(goal)
        return {**context, "domain": "business", "subdomain": subdomain, "domain_context": business_domain_engine.build_business_context(subdomain)}
