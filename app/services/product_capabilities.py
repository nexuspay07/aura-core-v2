"""Trusted product-mode capability policy.

This policy controls which Aura OS product experiences are exposed.  It does
not replace tenant or membership authorization, which remains enforced by the
existing resource services and routes.
"""

from __future__ import annotations

from dataclasses import dataclass


PERSONAL = "personal"
BUSINESS = "business"
ENTERPRISE = "enterprise"
SUPPORTED_PRODUCT_MODES = frozenset({PERSONAL, BUSINESS, ENTERPRISE})


_CAPABILITIES_BY_MODE = {
    PERSONAL: frozenset(
        {
            "home",
            "personal_home",
            "ask_aura",
            "decisions",
            "goals",
            "actions",
            "personal_context",
            "documents",
        }
    ),
    BUSINESS: frozenset(
        {
            "home",
            "ask_aura",
            "session_history",
            "documents",
            "organizations",
            "workspaces",
            "members",
            "marketplace",
            "simulations",
            "billing",
            "business_settings",
        }
    ),
    ENTERPRISE: frozenset(
        {
            "home",
            "ask_aura",
            "session_history",
            "documents",
            "organizations",
            "workspaces",
            "members",
            "marketplace",
            "simulations",
            "billing",
            "business_settings",
            "enterprise_settings",
        }
    ),
}


@dataclass(frozen=True)
class ProductCapabilities:
    """A safe, UI-facing projection of the trusted account context."""

    product_mode: str
    capabilities: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "product_mode": self.product_mode,
            "capabilities": list(self.capabilities),
        }


def resolve_product_capabilities(account_type: str | None) -> ProductCapabilities:
    """Resolve only from persisted account state; legacy values remain Business."""

    product_mode = account_type if account_type in SUPPORTED_PRODUCT_MODES else BUSINESS
    return ProductCapabilities(
        product_mode=product_mode,
        capabilities=tuple(sorted(_CAPABILITIES_BY_MODE[product_mode])),
    )
