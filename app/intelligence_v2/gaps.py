"""Decision-type-specific information-gap detection for Decision V2."""

import re

from app.intelligence_v2.contracts import ClarificationPlan, DecisionClassification, DecisionRequest, DecisionType, GapImportance, InformationGap


_OPERATIONAL_GAPS = (
    ("current_cost_baseline", "A baseline is required to quantify the savings target and measure improvement.", GapImportance.CRITICAL, "Without it, a cost-reduction plan cannot be measured.", False, "What is your current cost per delivery or order?"),
    ("cost_breakdown", "Cost components identify which levers can reduce cost without harming service.", GapImportance.CRITICAL, "The wrong cost lever can worsen service quality.", False, "What are the largest delivery cost components (for example labor, fuel, carrier fees, maintenance, or rework)?"),
    ("delivery_volume", "Volume determines fixed-cost absorption and the practical savings opportunity.", GapImportance.HIGH, "Savings estimates may be materially wrong.", False, "What is your average monthly delivery or order volume?"),
    ("service_level_baseline", "On-time and service-quality baselines protect the stated service constraint.", GapImportance.CRITICAL, "Cost cuts could silently reduce customer service.", False, "What are your current on-time delivery rate and service-level target?"),
    ("process_or_carrier_model", "The operating model determines which interventions are feasible.", GapImportance.HIGH, "Recommended actions may not apply to your network.", False, "Do you use your own fleet, third-party carriers, or a mix?"),
    ("major_delay_causes", "Delay causes identify the root constraints behind customer complaints.", GapImportance.HIGH, "The plan may treat symptoms rather than causes.", True, "What are the main causes of late deliveries today?"),
)


class InformationGapDetector:
    def detect(self, request: DecisionRequest, classification: DecisionClassification) -> list[InformationGap]:
        if classification.decision_type not in {DecisionType.COST_REDUCTION, DecisionType.OPERATIONAL_OPTIMIZATION, DecisionType.SUPPLY_CHAIN}:
            return []
        text = request.user_query.lower()
        profile = request.business_context.get("business_profile", {})
        facts = " ".join(item.content or "" for item in request.known_facts).lower()
        available = f"{text} {facts} {' '.join(str(value) for value in profile.values() if value)}"
        gaps = []
        for field, why, importance, impact, can_proceed, question in _OPERATIONAL_GAPS:
            if not self._has_evidence(field, available):
                gaps.append(InformationGap(field, why, importance, impact, can_proceed, question))
        # Query-derived target, timeframe, and explicit quality constraints are facts,
        # not missing fields. Other decisions will receive their own maps later.
        return gaps

    @staticmethod
    def _has_evidence(field: str, available: str) -> bool:
        """Terms alone are not evidence: a service-quality goal is not an SLA baseline."""
        if field == "current_cost_baseline":
            return bool(re.search(r"(?:\$\s*\d+(?:\.\d+)?\s*(?:per|/)|cost\s*(?:per|/))", available))
        if field == "cost_breakdown":
            return any(signal in available for signal in ("fuel", "carrier fee", "labor", "maintenance", "breakdown"))
        if field == "delivery_volume":
            return bool(re.search(r"\d+\s*(?:deliveries|orders|shipments)\s*(?:per|/)\s*(?:month|week|day)", available))
        if field == "service_level_baseline":
            return bool(re.search(r"(?:on-time|sla|service level|delivery rate)[^\d%]{0,24}\d+(?:\.\d+)?\s*%|\d+(?:\.\d+)?\s*%[^a-z]{0,24}(?:on-time|sla|service level|delivery rate)", available))
        if field == "process_or_carrier_model":
            return any(signal in available for signal in ("fleet", "carrier", "third-party", "3pl", "in-house"))
        return any(signal in available for signal in ("delay cause", "late because", "root cause", "traffic", "capacity"))

    def clarification_plan(self, gaps: list[InformationGap]) -> ClarificationPlan:
        blocking = [gap for gap in gaps if gap.importance == GapImportance.CRITICAL]
        nonblocking = [gap for gap in gaps if gap.importance != GapImportance.CRITICAL]
        ranked = blocking + nonblocking
        questions = [gap.suggested_question for gap in ranked[:5]]
        return ClarificationPlan(bool(blocking), questions, blocking, nonblocking, not blocking)


information_gap_detector = InformationGapDetector()
