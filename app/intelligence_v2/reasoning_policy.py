"""Small deterministic reasoning-effort policy; explicit configuration wins."""
from app.intelligence_v2.contracts import DecisionType
from app.intelligence_v2.model_provider import explicit_reasoning_effort

def select_reasoning_effort(state):
    override=explicit_reasoning_effort()
    if override: return override, "environment_override"
    if state.evidence_conflicts or state.classification.decision_type in {DecisionType.OPERATIONAL_OPTIMIZATION,DecisionType.COST_REDUCTION,DecisionType.FINANCIAL_PLANNING,DecisionType.INVESTMENT}: return "medium", "decision_complexity"
    personal={DecisionType.CAREER_DECISION,DecisionType.MAJOR_PURCHASE,DecisionType.PERSONAL_PROJECT,DecisionType.EDUCATION_DECISION,DecisionType.LIFE_PLANNING}
    if state.classification.decision_type in personal and not state.information_gaps and not state.assumptions: return "none", "straightforward_personal_comparison"
    return "low", "personal_ambiguity_or_additional_tradeoffs"
