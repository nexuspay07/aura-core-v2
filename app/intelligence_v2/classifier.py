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


_PERSONAL_RULES: dict[DecisionType, tuple[set[str], set[str]]] = {
    DecisionType.CAREER_DECISION: ({"job", "career", "promotion", "work", "role"}, {"job offer", "leave my job", "current job", "hate my job", "career change"}),
    DecisionType.EDUCATION_DECISION: ({"school", "college", "university", "degree", "education", "study", "tuition"}, {"go back to school", "return to school"}),
    DecisionType.MAJOR_PURCHASE: ({"car", "home", "house", "purchase", "buy", "buying"}, {"major purchase", "buying a car", "buy a car"}),
    DecisionType.PERSONAL_FINANCE: ({"savings", "budget", "debt", "afford", "income", "expenses", "retirement"}, {"personal finance", "emergency fund", "financial security"}),
    DecisionType.RELOCATION: ({"move", "moving", "relocate", "relocation", "city", "country"}, {"move to", "moving to"}),
    DecisionType.PERSONAL_PROJECT: ({"project", "side", "build", "create", "start"}, {"personal project", "side project", "side business"}),
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
