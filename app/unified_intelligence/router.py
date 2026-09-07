"""Deterministic first-pass capability routing; client hints are never trusted."""
from __future__ import annotations

import re

from app.unified_intelligence.contracts import Capability, CapabilityRoute
from app.intelligence_v2.classifier import has_personal_decision_intent, is_personal_decision_continuation


_CURRENT = re.compile(r"\b(today|currently|current(?!\s+(?:job|role|employer|situation|plan))|latest|right now|just happened|breaking)\b", re.I)
_CURRENT_PERIOD = re.compile(r"\bthis (?:week|month|morning)\b", re.I)
_CURRENT_PERIOD_SUBJECT = re.compile(r"\b(?:news|stories?|announcements?|happened|happening|politics|political|economic|events?|developments?|updates?|results?|rates?|prices?|weather)\b", re.I)
_CURRENT_FOLLOWUP = re.compile(r"\b(?:explain|expand on|tell me more about) (?:the )?(?:first|second|third|fourth|last) (?:one|story|item|source)\b", re.I)
_DOCUMENT = re.compile(r"\b(this|the|my|uploaded|attached) (?:document|file|report|contract|offer|policy|resume|cv)\b", re.I)
_LEGACY_DECISION = re.compile(r"\b(i (?:have|received) two job offers|i(?:'m| am) deciding whether|i(?:'m| am) thinking about (?:buying|leaving|moving|enrolling|accepting)|i may leave my (?:current )?(?:job|career)|do i (?:buy|take|choose|leave|move|enroll|accept))\b", re.I)
_PERSONAL = re.compile(r"\b(for me|my (?:savings|budget|career|job|family|goals?|priorities|situation|plans?|constraints?|preferences?))\b", re.I)
_SOCIAL = re.compile(r"^(?:hi|hello|hey|thanks|thank you|good (?:morning|afternoon|evening))[!. ]*$", re.I)


class UnifiedCapabilityRouter:
    def route(self, message: str, *, prior_user_turns: list[str] | None = None) -> CapabilityRoute:
        text = message.strip()
        if _SOCIAL.match(text):
            return CapabilityRoute("conversation", (Capability.GENERAL,), requires_language_model=False, routing_reason="clear social turn")

        current = bool(
            _CURRENT.search(text)
            or _CURRENT_FOLLOWUP.search(text)
            or (_CURRENT_PERIOD.search(text) and _CURRENT_PERIOD_SUBJECT.search(text))
        )
        document = bool(_DOCUMENT.search(text))
        decision = bool(
            _LEGACY_DECISION.search(text)
            or has_personal_decision_intent(text)
            or is_personal_decision_continuation(text, prior_user_turns)
        )
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
