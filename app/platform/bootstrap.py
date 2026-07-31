"""Explicit installation point for production Aura OS capabilities."""

from app.domains.business.domain import BusinessDomain
from app.platform.ai import AIOrchestrator, DeterministicProvider, ProviderRegistry
from app.platform.extensions import ExtensionCatalog
from app.platform.object_registry import PlatformObjectRegistry
from app.platform.objects import Decision, Goal, KnowledgeDocument, Project, Task, TimelineEvent
from app.platform.registry import PlatformRegistry


platform_registry = PlatformRegistry()
platform_registry.register_domain(BusinessDomain)

provider_registry = ProviderRegistry()
provider_registry.register(DeterministicProvider())
ai_orchestrator = AIOrchestrator(provider_registry)
extension_catalog = ExtensionCatalog()
object_registry = PlatformObjectRegistry()
for object_type in (Goal, Project, Task, Decision, TimelineEvent, KnowledgeDocument):
    object_registry.register(object_type)
