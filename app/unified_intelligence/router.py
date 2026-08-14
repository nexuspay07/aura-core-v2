"""Deterministic first-pass capability routing; client hints are never trusted."""
from __future__ import annotations

import re

from app.unified_intelligence.contracts import Capability, CapabilityRoute


_CURRENT = re.compile(r"\b(today|tonight|currently|current(?!\s+(?:job|role|employer|situation|plan))|latest|right now|this (?:week|month|morning)|just happened|breaking)\b", re.I)
_DOCUMENT = re.compile(r"\b(this|the|my|uploaded|attached) (?:document|file|report|contract|offer|policy|resume|cv)\b", re.I)
_DECISION = re.compile(r"\b(should i|which (?:one|option) should i|help me decide|is it (?:worth|a good idea)|would it be better (?:for me )?to|do i (?:buy|take|choose|leave|move|enroll|accept)|i (?:have|received) two job offers|i(?:'m| am) deciding whether|i(?:'m| am) thinking about (?:buying|leaving|moving|enrolling|accepting)|i may leave my (?:current )?(?:job|career))\b", re.I)
_PERSONAL = re.compile(r"\b(for me|my (?:savings|budget|career|job|family|goals?|priorities|situation|plans?|constraints?|preferences?))\b", re.I)
_SOCIAL = re.compile(r"^(?:hi|hello|hey|thanks|thank you|good (?:morning|afternoon|evening))[!. ]*$", re.I)


class UnifiedCapabilityRouter:
    def route(self, message: str) -> CapabilityRoute:
        text = message.strip()
        if _SOCIAL.match(text):
            return CapabilityRoute("conversation", (Capability.GENERAL,), requires_language_model=False, routing_reason="clear social turn")

        current = bool(_CURRENT.search(text))
        document = bool(_DOCUMENT.search(text))
        decision = bool(_DECISION.search(text))
        personal = decision or bool(_PERSONAL.search(text))
        capabilities: list[Capability] = []
        if current:
            capabilities.append(Capability.CURRENT)
        if document:
            capabilities.append(Capability.DOCUMENT)
        if personal:
            capabilities.append(Capability.PERSONAL)
        if decision:
            capabilities.append(Capability.DECISION)
        if not decision:
            capabilities.append(Capability.GENERAL)

        intent = "decision" if decision else "current_information" if current else "document_question" if document else "general"
        # Current retrieval is a deterministic availability boundary for Alpha.
        needs_model = not current or document or personal
        return CapabilityRoute(
            intent, tuple(dict.fromkeys(capabilities)),
            requires_current_information=current,
            requires_personal_context=personal,
            requires_decision_analysis=decision,
            requires_document_evidence=document,
            requires_language_model=needs_model,
            routing_reason="server policy selected required capabilities",
        )


unified_capability_router = UnifiedCapabilityRouter()
