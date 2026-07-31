from app.tenants.registry import get_tenant_config


class TenantManager:
    """
    Centralized Tenant Manager.

    Responsible for:
    - Retrieving tenant configuration
    - Validating tenant existence
    - Providing a single entry point for tenant-related operations

    Future responsibilities:
    - Load tenants from the database
    - Cache tenant configurations
    - Manage tenant lifecycle
    - Validate tenant subscriptions/plans
    """

    @staticmethod
    def get_tenant_config(tenant_id: str):
        """
        Retrieve a tenant configuration.

        Args:
            tenant_id: Unique tenant identifier.

        Returns:
            TenantConfig

        Raises:
            ValueError: If the tenant does not exist.
        """

        config = get_tenant_config(tenant_id)

        if config is None:
            raise ValueError(f"Tenant '{tenant_id}' was not found.")

        return config

    @staticmethod
    def tenant_exists(tenant_id: str) -> bool:
        """
        Check whether a tenant exists.
        """
        return get_tenant_config(tenant_id) is not None


tenant_manager = TenantManager()