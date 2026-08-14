from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Capability(str, Enum):
    GENERAL = "general"
    CURRENT = "current"
    PERSONAL = "personal"
    DOCUMENT = "document"
    DECISION = "decision"


@dataclass(frozen=True)
class CapabilityRoute:
    primary_intent: str
    capabilities_required: tuple[Capability, ...]
    requires_current_information: bool = False
    requires_personal_context: bool = False
    requires_decision_analysis: bool = False
    requires_document_evidence: bool = False
    requires_language_model: bool = True
    confidence: str = "high"
    routing_reason: str = ""


@dataclass(frozen=True)
class ModelRequest:
    capability: str
    system: str
    prompt: str
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ModelResult:
    content: str
    usage: dict[str, Any] = field(default_factory=dict)

