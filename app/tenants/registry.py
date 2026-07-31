from typing import Dict, List, Optional

from .tenant_config import TenantConfig


# ==========================================================
# TENANT REGISTRY
# ==========================================================

TENANTS: Dict[str, TenantConfig] = {

    "hospital_001": TenantConfig(
        tenant_id="hospital_001",
        adapter="local",
        plan="enterprise",
    ),

    "school_001": TenantConfig(
        tenant_id="school_001",
        adapter="local",
        plan="basic",
    ),

    "startup_001": TenantConfig(
        tenant_id="startup_001",
        adapter="openai",
        plan="pro",
    ),
}


# ==========================================================
# GET TENANT
# ==========================================================

def get_tenant_config(
    tenant_id: str,
) -> Optional[TenantConfig]:
    """
    Retrieve a tenant configuration.

    Returns:
        TenantConfig | None
    """

    return TENANTS.get(tenant_id)


# ==========================================================
# CHECK TENANT
# ==========================================================

def tenant_exists(
    tenant_id: str,
) -> bool:
    """
    Check whether a tenant exists.
    """

    return tenant_id in TENANTS


# ==========================================================
# LIST TENANTS
# ==========================================================

def list_tenants() -> List[TenantConfig]:
    """
    Return every registered tenant.
    """

    return list(TENANTS.values())


# ==========================================================
# REGISTER TENANT
# ==========================================================

def register_tenant(
    config: TenantConfig,
):
    """
    Register a new tenant.
    """

    TENANTS[config.tenant_id] = config


# ==========================================================
# REMOVE TENANT
# ==========================================================

def remove_tenant(
    tenant_id: str,
) -> bool:
    """
    Remove a tenant.

    Returns:
        True if removed.
        False if not found.
    """

    return TENANTS.pop(tenant_id, None) is not None