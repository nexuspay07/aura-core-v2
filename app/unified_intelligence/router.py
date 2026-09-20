"""Deterministic first-pass capability routing; client hints are never trusted."""
from __future__ import annotations

import re

from app.unified_intelligence.contracts import Capability, CapabilityRoute
from app.intelligence_v2.classifier import has_explicit_option_list, has_personal_decision_intent, is_personal_decision_continuation


_TEMPORAL = re.compile(r"\b(today|currently|current|recent(?:ly)?|latest|right now|just happened|breaking)\b", re.I)
_CURRENT_PERIOD = re.compile(r"\bthis (?:week|month|morning)\b", re.I)
_CURRENT_PERIOD_SUBJECT = re.compile(r"\b(?:news|stories?|announcements?|happened|happening|politics|political|economic|events?|developments?|updates?|results?|rates?|prices?|weather)\b", re.I)
_CURRENT_FOLLOWUP = re.compile(r"\b(?:explain|expand on|tell me more about) (?:the )?(?:first|second|third|fourth|last) (?:one|story|item|source)\b", re.I)
_DOCUMENT = re.compile(r"\b(this|the|my|uploaded|attached) (?:document|file|report|contract|offer|policy|resume|cv)\b", re.I)
_LEGACY_DECISION = re.compile(r"\b(i (?:have|received) two job offers|i(?:'m| am) deciding whether|i(?:'m| am) thinking about (?:buying|leaving|moving|enrolling|accepting)|i may leave my (?:current )?(?:job|career)|do i (?:buy|take|choose|leave|move|enroll|accept))\b", re.I)
_PERSONAL = re.compile(r"\b(for me|my (?:savings|budget|career|job|family|goals?|priorities|situation|plans?|constraints?|preferences?))\b", re.I)
_SOCIAL = re.compile(r"^(?:hi|hello|hey|thanks|thank you|good (?:morning|afternoon|evening))[!. ]*$", re.I)
_DECISION_DELIVERABLE = re.compile(
    r"\b(?:recommend(?:ation|ed| a path)?|trade-?offs?|risks?|opportunity costs?|decision analysis|"
    r"what (?:could|would) change (?:this|the recommendation)|(?:prioriti[sz]e|compare) (?:these|the|my|our)|"
    r"plan (?:after|following|for) (?:the|my|our|this) (?:choice|decision|path))\b", re.I,
)
_COMPARE_ALTERNATIVES = re.compile(r"\bcompare\b.{0,100}\b(?:paths?|options?|choices?|alternatives?|versus|vs\.?|or)\b", re.I | re.S)
_COMPARE_SUPPLIED = re.compile(r"\bcompare\s+(?:these|the|my|our)?\s*(?:two|three|four)?\s*(?:job offers?|paths?|options?|choices?|alternatives?|courses?|plans?|approaches?)\b", re.I)
_OPTION_HEADER = re.compile(r"\b(?:two|three|four|2|3|4)?\s*(?:paths?|options?|choices?|alternatives?)\s*(?:are|include|:)", re.I)
_USER_TEMPORAL_CONTEXT = re.compile(
    r"\b(?:i(?:'m| am)?|we(?:'re| are)?)\s+currently\b|\b(?:my|our)\s+current\b|"
    r"\b(?:i|we)\s+currently\b", re.I,
)
_EXTERNAL_QUERY = re.compile(
    r"\b(?:what|which|who|where|when|how|is|are|does|do|has|have|find|check|verify|tell me)\b"
    r"[^?.!]{0,180}\b(?:today|currently|current|recent(?:ly)?|latest|right now)\b|"
    r"\b(?:today|currently|current|recent(?:ly)?|latest|right now)\b[^?.!]{0,180}"
    r"\b(?:what|which|who|where|when|how|competitive|markets?|news|stories?|rates?|prices?|law|regulation|requirements?|tuition)\b",
    re.I,
)
_MATERIAL_EXTERNAL_BASIS = re.compile(
    r"\b(?:given|based on|according to|under)\s+(?:the\s+)?(?:current|latest|recent)\b|"
    r"\b(?:competitive|above market|below market)\b[^?.!]{0,80}\b(?:currently|right now|today|market)\b|"
    r"\b(?:currently|right now|today)\b[^?.!]{0,80}\b(?:competitive|above market|below market)\b",
    re.I,
)
_SUPPLIED_DECISION_CONTEXT = re.compile(
    r"\b(?:my|our|i|we)\b[^.!?]{0,160}(?:\$\s*[\d,]+|\b\d+(?:\.\d+)?\b|"
    r"\b(?:options?|alternatives?|goals?|constraints?|priorities|plans?|salary|customers?|budget|commute|responsibilities)\b)",
    re.I,
)


def has_structured_decision_intent(text: str) -> bool:
    """Recognize bounded decision structure, independently of topic keywords."""
    header = _OPTION_HEADER.search(text)
    numbered = len(re.findall(r"(?:^|[\s;])\d+[.)]\s+", text[header.end():header.end() + 1200] if header else ""))
    alternatives = has_explicit_option_list(text) or bool(_COMPARE_ALTERNATIVES.search(text) or _COMPARE_SUPPLIED.search(text)) or bool(header and numbered >= 2)
    return alternatives and bool(_DECISION_DELIVERABLE.search(text))


def requires_external_freshness(text: str) -> bool:
    """Return true only for a requested unresolved current-world dependency."""
    if not _TEMPORAL.search(text) and not _CURRENT_PERIOD.search(text):
        return bool(_CURRENT_FOLLOWUP.search(text))
    # Remove temporal markers that grammatically describe first-person supplied
    # context; another temporal request in the same message remains detectable.
    external_text = _USER_TEMPORAL_CONTEXT.sub("user supplied context", text)
    return bool(
        _CURRENT_FOLLOWUP.search(external_text)
        or (_CURRENT_PERIOD.search(external_text) and _CURRENT_PERIOD_SUBJECT.search(external_text))
        or _EXTERNAL_QUERY.search(external_text)
        or _MATERIAL_EXTERNAL_BASIS.search(external_text)
    )


class UnifiedCapabilityRouter:
    def route(self, message: str, *, prior_user_turns: list[str] | None = None) -> CapabilityRoute:
        text = message.strip()
        if _SOCIAL.match(text):
            return CapabilityRoute("conversation", (Capability.GENERAL,), requires_language_model=False, routing_reason="clear social turn", routing_event="route_other")

        current = requires_external_freshness(text)
        document = bool(_DOCUMENT.search(text))
        decision_detected = bool(
            _LEGACY_DECISION.search(text)
            or has_personal_decision_intent(text)
            or has_structured_decision_intent(text)
            or is_personal_decision_continuation(text, prior_user_turns)
        )
        supplied_context = has_structured_decision_intent(text) or bool(_SUPPLIED_DECISION_CONTEXT.search(text) or _PERSONAL.search(text))
        freshness_dependent_decision = decision_detected and current and not supplied_context
        decision = decision_detected and not freshness_dependent_decision
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
        routing_event = (
            "route_decision_hybrid" if decision and current else
            "route_decision_freshness_dependent" if freshness_dependent_decision else
            "route_decision_self_contained" if decision else
            "route_current_information" if current else
            "route_other"
        )
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
            routing_event=routing_event,
            freshness_source="external_dependency" if current else ("user_context" if _TEMPORAL.search(text) else None),
        )


unified_capability_router = UnifiedCapabilityRouter()
