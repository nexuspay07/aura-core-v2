from fastapi import APIRouter
from app.platform.bootstrap import extension_catalog, object_registry, platform_registry, provider_registry

router = APIRouter(
    prefix="/platform",
    tags=["Platform"]
)

@router.get("/status")
def platform_status():
    return {
        "platform": "Aura AI Platform Layer",
        "status": "ACTIVE"
    }


@router.get("/manifest")
def platform_manifest():
    """Read-only installed-capability manifest for future dynamic clients."""
    platform = platform_registry.manifest()
    platform.update(extension_catalog.manifest())
    platform["object_types"] = object_registry.manifest()
    platform["ai_providers"] = [{"key": key, "healthy": provider_registry.healthy(key)} for key in provider_registry.keys()]
    return {"success": True, "platform": platform}
