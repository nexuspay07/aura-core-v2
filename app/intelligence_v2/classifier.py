"""Deterministic, explainable Decision V2 taxonomy classifier.

Rules score multiple semantic indicator groups instead of selecting the first
substring match. The interface is intentionally replaceable by a model later.
"""

import re

from app.intelligence_v2.contracts import DecisionClassification, DecisionType


_RULES: dict[DecisionType, tuple[list[tuple[set[str], float]], list[str]]] = {
    DecisionType.CAREER_DECISION: ([({"job offer", "job offers", "career growth", "promotion", "commute", "remote"}, 4.0), ({"offer a", "offer b", "candidate", "salary", "evenings"}, 2.0)], ["priorities", "compensation", "lifestyle_impact", "growth_opportunity", "constraints"]),
    DecisionType.EDUCATION_DECISION: ([({"return to school", "college program", "degree", "education"}, 4.0), ({"tuition", "opportunity cost", "program", "study"}, 2.0)], ["intended_outcome", "time_commitment", "alternatives", "financial_runway"]),
    DecisionType.MAJOR_PURCHASE: ([({"buying a", "purchase", "current car", "car"}, 3.5), ({"saved", "emergencies", "unreliable"}, 2.0)], ["purchase_cost", "resources", "financial_buffer", "necessity"]),
    DecisionType.PERSONAL_PROJECT: ([({"personal project", "online business", "side project"}, 3.5), ({"hours per week", "working full time", "initially"}, 2.0)], ["objective", "available_time", "available_budget", "constraints"]),
    DecisionType.COST_REDUCTION: ([({"reduce", "cut", "lower", "decrease", "save"}, 2.0), ({"cost", "costs", "expense", "expenses", "spend", "waste"}, 2.5)], ["cost_baseline", "cost_breakdown", "volume", "constraints"]),
    DecisionType.OPERATIONAL_OPTIMIZATION: ([({"operation", "operations", "process", "workflow", "efficiency", "delivery", "delay", "late", "throughput"}, 2.0)], ["process_model", "service_level", "volume", "delay_causes"]),
    DecisionType.SUPPLY_CHAIN: ([({"delivery", "fleet", "carrier", "route", "logistics", "shipping", "supplier", "inventory", "warehouse"}, 2.0)], ["network_model", "carrier_or_fleet_mix", "service_level", "volume"]),
    DecisionType.PRICING: ([({"price", "pricing", "discount", "margin", "package", "rate"}, 2.5)], ["unit_economics", "customer_segments", "competitive_prices"]),
    DecisionType.HIRING: ([({"hire", "hiring", "recruit", "headcount", "employee", "team"}, 2.5)], ["workload", "role_definition", "budget", "capacity"]),
    DecisionType.MARKET_EXPANSION: ([({"expand", "expansion", "new market", "geography", "international", "region"}, 2.5)], ["market_size", "entry_constraints", "customer_demand"]),
    DecisionType.INVESTMENT: ([({"invest", "investment", "capex", "capital", "acquire asset"}, 2.5)], ["investment_amount", "returns", "cash_flow", "alternatives"]),
    DecisionType.PRODUCT_LAUNCH: ([({"launch", "release", "introduce", "new product", "go to market"}, 2.5)], ["customer_problem", "readiness", "launch_plan"]),
    DecisionType.SALES_GROWTH: ([({"sales", "pipeline", "leads", "revenue growth", "conversion"}, 2.5)], ["sales_funnel", "customer_segments", "revenue_baseline"]),
    DecisionType.CUSTOMER_RETENTION: ([({"retain", "retention", "churn", "renewal", "complaint", "complaints", "satisfaction"}, 2.0)], ["retention_baseline", "customer_feedback", "service_level"]),
    DecisionType.FINANCIAL_PLANNING: ([({"budget", "cash flow", "forecast", "financial plan", "profitability"}, 2.5)], ["financial_statements", "cash_flow", "forecast_horizon"]),
    DecisionType.RISK_MANAGEMENT: ([({"risk", "compliance", "exposure", "mitigate", "contingency"}, 2.5)], ["risk_register", "controls", "risk_appetite"]),
    DecisionType.STRATEGIC_PLANNING: ([({"strategy", "strategic", "vision", "priority", "priorities"}, 1.5)], ["objectives", "constraints", "alternatives"]),
}


class DecisionClassifier:
    def classify(self, query: str) -> DecisionClassification:
        normalized = query.lower()
        tokens = set(re.findall(r"[a-z]+", normalized))
        explicit_resource_choice = bool(
            re.search(r"\boptions?\s+(?:are|include|:)\b", normalized)
            or (re.search(r"\bshould we\b", normalized) and re.search(r"\bor\b", normalized))
        )
        scores: dict[DecisionType, float] = {}
        reasons: dict[DecisionType, list[str]] = {}
        for decision_type, (groups, _) in _RULES.items():
            score = 0.0
            hits: list[str] = []
            for terms, weight in groups:
                phrases = {term for term in terms if " " in term}
                matched_phrases = [phrase for phrase in phrases if phrase in normalized]
                matched_tokens = sorted((terms - phrases) & tokens)
                if matched_phrases or matched_tokens:
                    score += weight
                    hits.extend(matched_phrases + matched_tokens)
            if score:
                scores[decision_type] = score
                reasons[decision_type] = hits

        if not scores:
            return DecisionClassification(
                decision_type=DecisionType.GENERAL_BUSINESS_ANALYSIS,
                secondary_types=[], confidence=0.25,
                rationale=["No decision-specific evidence was found in the request."],
                required_data_domains=["objective", "constraints", "available_business_context"],
            )

        # A stated multi-option company resource choice is strategic even when
        # individual options mention expenses or hiring. Those mentions are
        # evidence about the alternatives, not necessarily the primary intent.
        if explicit_resource_choice:
            secondary = sorted(
                (item for item in scores if item is not DecisionType.STRATEGIC_PLANNING),
                key=lambda item: (-scores[item], item.value),
            )[:3]
            return DecisionClassification(
                decision_type=DecisionType.STRATEGIC_PLANNING,
                secondary_types=secondary,
                confidence=0.82,
                rationale=["strategic_planning indicators: explicit multi-option business resource choice"],
                required_data_domains=["objectives", "constraints", "alternatives"],
            )

        ranked = sorted(scores, key=lambda item: (-scores[item], item.value))
        primary = ranked[0]
        secondary = [item for item in ranked[1:] if scores[item] >= max(1.5, scores[primary] * 0.4)]
        required = list(_RULES[primary][1])
        for item in secondary:
            for domain in _RULES[item][1]:
                if domain not in required:
                    required.append(domain)
        confidence = min(0.9, 0.4 + scores[primary] * 0.12 + (0.08 if len(reasons[primary]) > 1 else 0))
        return DecisionClassification(
            decision_type=primary,
            secondary_types=secondary,
            confidence=round(confidence, 2),
            rationale=[f"{primary.value} indicators: {', '.join(reasons[primary])}"] + ([f"secondary {item.value}: {', '.join(reasons[item])}" for item in secondary]),
            required_data_domains=required,
        )


decision_classifier = DecisionClassifier()


_DECISION_INTENT_PATTERNS = (
    re.compile(r"\b(?:should i|do you think i should|which (?:one|option|choice)|which of (?:these|the) options|what would you do|what do you recommend)\b", re.I),
    re.compile(r"\b(?:help me (?:decide|choose)|i (?:can(?:not|'t)|do not|don't) decide|i (?:do not|don't) know (?:what|which|whether) to choose)\b", re.I),
    re.compile(r"\b(?:i(?:'m| am) torn between|i have (?:two|multiple) (?:choices|options)|choose between|decide between)\b", re.I),
    re.compile(r"\b(?:is|would) .{0,80}\b(?:sensible|a good idea|worth it)\b(?:.{0,30}\bfor me\b)?", re.I),
    re.compile(r"\b(?:would it be better to|i (?:can(?:not|'t)|do not|don't) decide whether|i do not know whether|i don't know whether)\b", re.I),
)
_PERSONAL_GOAL_WITH_CONSTRAINT = re.compile(
    r"\bi (?:want|need|plan|intend) to (?:start|launch|move|relocate|leave|buy|enroll|study|build|create)\b"
    r"(?=.{0,160}(?:\$|\bbudget\b|\bwithin\b|\bin \d+\s+(?:days?|weeks?|months?|years?)\b))",
    re.I,
)
_DECISION_CONTINUATION = re.compile(
    r"\b(?:actually|instead|changed my mind|no longer|anymore|only have|maximum budget|new budget|new deadline|need (?:it|this) (?:done )?(?:within|in))\b",
    re.I,
)


def has_personal_decision_intent(text: str) -> bool:
    """Recognize a request for a personal choice/recommendation, not information."""
    value = text.strip()
    return bool(any(pattern.search(value) for pattern in _DECISION_INTENT_PATTERNS) or _PERSONAL_GOAL_WITH_CONSTRAINT.search(value) or re.search(r"\b(?:should|could) we\b|\bhelp (?:us|our company) (?:decide|choose)\b", value, re.I))


def is_personal_decision_continuation(text: str, prior_user_turns: list[str] | None) -> bool:
    """Treat an explicit correction as decision work only in an active decision context."""
    if not _DECISION_CONTINUATION.search(text):
        return False
    return any(has_personal_decision_intent(turn) for turn in (prior_user_turns or [])[-12:])


_PERSONAL_RULES: dict[DecisionType, tuple[set[str], set[str]]] = {
    DecisionType.CAREER_DECISION: ({"job", "career", "promotion", "work", "role"}, {"job offer", "leave my job", "current job", "hate my job", "career change"}),
    DecisionType.EDUCATION_DECISION: ({"school", "college", "university", "degree", "education", "study", "tuition", "course", "certificate", "diploma"}, {"go back to school", "return to school", "choose a course"}),
    DecisionType.MAJOR_PURCHASE: ({"car", "home", "house", "purchase", "buy", "buying"}, {"major purchase", "buying a car", "buy a car"}),
    DecisionType.PERSONAL_FINANCE: ({"savings", "budget", "debt", "afford", "income", "expenses", "retirement"}, {"personal finance", "emergency fund", "financial security"}),
    DecisionType.RELOCATION: ({"move", "moving", "relocate", "relocation", "city", "country"}, {"move to", "moving to"}),
    DecisionType.PERSONAL_PROJECT: (
        {"project", "side", "build", "create", "start", "launch", "business", "service", "product", "cleaning", "tutoring"},
        {"personal project", "side project", "side business", "cleaning business", "cleaning company", "tutoring service"},
    ),
}


def classify_personal(query: str) -> DecisionClassification:
    """Classify Personal decisions without allowing Business taxonomy leakage."""
    normalized = query.lower()
    tokens = set(re.findall(r"[a-z]+", normalized))
    scores: dict[DecisionType, float] = {}
    hits: dict[DecisionType, list[str]] = {}
    for decision_type, (words, phrases) in _PERSONAL_RULES.items():
        matched_phrases = sorted(phrase for phrase in phrases if phrase in normalized)
        matched_words = sorted(words & tokens)
        score = len(matched_words) + 3 * len(matched_phrases)
        if score:
            scores[decision_type] = float(score)
            hits[decision_type] = [*matched_phrases, *matched_words]
    if not scores:
        return DecisionClassification(DecisionType.LIFE_PLANNING, [], 0.35, ["No narrower Personal decision category was established."], ["objective", "options", "priorities", "constraints"])
    ranked = sorted(scores, key=lambda item: (-scores[item], item.value))
    primary = ranked[0]
    secondary = [item for item in ranked[1:] if scores[item] >= max(2, scores[primary] * 0.55)]
    domains = list(_RULES.get(primary, ([], ["objective", "options", "priorities", "constraints"]))[1])
    return DecisionClassification(primary, secondary, min(0.92, round(0.48 + scores[primary] * 0.07, 2)), [f"Personal {primary.value} indicators: {', '.join(hits[primary])}"], domains)
