from dataclasses import dataclass
from typing import Optional


@dataclass
class TenantConfig:
    """
    Tenant configuration model.

    This class represents a single tenant's configuration.

    Future versions may include:
    - AI model selection
    - Vector database provider
    - Memory limits
    - Token quotas
    - Feature flags
    - Billing information
    """

    # ==========================================================
    # IDENTITY
    # ==========================================================

    tenant_id: str

    # ==========================================================
    # AI
    # ==========================================================

    adapter: str = "local"

    model: str = "default"

    # ==========================================================
    # SUBSCRIPTION
    # ==========================================================

    plan: str = "free"

    # ==========================================================
    # FEATURES
    # ==========================================================

    memory_enabled: bool = True

    knowledge_enabled: bool = True

    vector_enabled: bool = True

    telemetry_enabled: bool = True

    # ==========================================================
    # OPTIONAL SETTINGS
    # ==========================================================

    organization_id: Optional[int] = None

    workspace_id: Optional[int] = None