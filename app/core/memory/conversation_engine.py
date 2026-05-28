import re

from app.domains.business.business_domain_engine import business_domain_engine
from app.domains.business.business_strategy_engine import business_strategy_engine


def extract_user_context(message: str):
    m = message.lower()
    budget = None
    market = None

    budget_match = re.search(r"\$?\s?(\d{3,7})", m)
    if budget_match:
        budget = int(budget_match.group(1))

    if any(x in m for x in ["low budget", "small budget", "little money", "cheap", "limited budget"]):
        budget = budget or 3000
    elif any(x in m for x in ["medium budget", "average budget", "normal budget"]):
        budget = budget or 10000
    elif any(x in m for x in ["high budget", "big budget", "large budget"]):
        budget = budget or 50000

    if any(x in m for x in [
        "competitive", "competition", "crowded", "saturated",
        "many competitors", "lots of competition", "too many businesses",
        "many businesses", "many similar businesses", "similar businesses",
        "similar business", "bigger competitors", "big competitors",
        "larger competitors", "established competitors"
    ]):
        market = "competitive"

    elif any(x in m for x in [
        "few competitors", "not many competitors", "not many businesses",
        "less crowded", "low competition", "no competition", "new market", "monopoly"
    ]):
        market = "monopoly"

    return {"budget": budget, "market": market}


class ConversationEngine:

    def detect_intent(self, message: str):
        m = message.lower()

        if any(x in m for x in [
            "pain", "fever", "cough", "headache", "fatigue",
            "shortness of breath", "dizziness", "symptom", "medical", "health"
        ]):
            return "healthcare_strategy"

        if any(x in m for x in [
            "grow", "startup", "business", "company", "scale",
            "customers", "revenue", "pricing", "price", "hire",
            "market", "cost", "expenses", "sales", "clients",
            "offline", "online", "shop", "store", "service",
            "restaurant", "food", "building materials", "construction"
        ]):
            return "business_strategy"

        if any(x in m for x in ["invest", "money", "portfolio", "budget", "finance", "returns"]):
            return "finance_strategy"

        return "general"

    def needs_clarification(self, message: str):
        return len(message.strip().split()) <= 3

    def build_clarification_question(self, intent: str):
        if intent == "business_strategy":
            return "Do you want help with growth, pricing, online vs offline, customers, cost control, or starting safely?"
        if intent == "healthcare_strategy":
            return "What symptom are you experiencing and how severe is it?"
        if intent == "finance_strategy":
            return "Are you looking for safer returns, balanced growth, or aggressive upside?"
        return "Can you clarify your goal?"

    def detect_business_subdomain(self, message: str):
        return business_domain_engine.detect_subdomain(message)

    def clean_goal_text(self, goal: str):
        cleaned = goal.strip()
        for prefix in ["I want to ", "i want to ", "I need to ", "i need to ", "I would like to ", "i would like to "]:
            if cleaned.startswith(prefix):
                cleaned = cleaned.replace(prefix, "", 1).strip()
        return cleaned

    def extract_preferences(self, message: str):
        m = message.lower()
        context = extract_user_context(message)

        preferences = {
            "risk_tolerance": 0.5,
            "budget": context.get("budget"),
            "market": context.get("market")
        }

        if any(x in m for x in ["low risk", "safe", "conservative", "safest"]):
            preferences["risk_tolerance"] = 0.2
        elif any(x in m for x in ["high risk", "aggressive", "fast growth"]):
            preferences["risk_tolerance"] = 0.8

        return preferences

    def build_profile_note(self, profile: dict | None):
        if not profile:
            return ""

        preferred_risk = profile.get("preferred_risk")
        interaction_count = profile.get("interaction_count", 0)

        if interaction_count < 2:
            return ""

        if preferred_risk == "low":
            return "AURA adjusted this response toward safer execution because your profile shows lower risk preference."
        if preferred_risk == "high":
            return "AURA adjusted this response toward faster execution because your profile shows higher growth preference."

        return "AURA used your previous interaction profile to keep the recommendation balanced."

    def build_conversational_response(
    self,
    goal: str,
    best: dict,
    explanation,
    profile: dict | None = None,
    pipeline_result: dict | None = None,
    memory_summary: dict | None = None
):
        profile = profile or {}
        pipeline_result = pipeline_result or {}
        operational_intelligence = pipeline_result.get("operational_intelligence", {})

        memory_summary = memory_summary or {}
        memory_note = self._build_memory_note(memory_summary)

        clean_goal = self.clean_goal_text(goal)
        business_intent = business_domain_engine.detect_subdomain(goal)

        preferences = self.extract_preferences(goal)
        scenario = pipeline_result.get("scenario", {})

        budget = preferences.get("budget") or scenario.get("budget") or 10000
        market = preferences.get("market") or scenario.get("market") or "normal"

        business_understanding = pipeline_result.get("business_understanding", {})
        business_dna = pipeline_result.get("business_dna", {})
        dynamic_reasoning = pipeline_result.get("dynamic_reasoning", {})
        market_intelligence = pipeline_result.get("market_intelligence", {})
        strategy_comparison = pipeline_result.get("strategy_comparison", {})
        prediction = pipeline_result.get("prediction", {})
        visual_intelligence = pipeline_result.get("visual_intelligence", {})

        business_strategy = business_strategy_engine.generate_strategy(
            business_intent,
            {
                "goal": goal,
                "risk": best.get("risk", "medium"),
                "strategy": best.get("name", "Balanced"),
                "budget": budget,
                "market": market
            }
        )

        next_steps = business_strategy.get("steps") or best.get("action_plan") or [
            "Clarify the customer problem",
            "Test with real users or customers",
            "Improve based on results"
        ]

        recommended_move = business_strategy.get(
            "advice",
            dynamic_reasoning.get(
                "current_priority",
                "Start small, validate demand, and improve before scaling."
            )
        )

        confidence = prediction.get("confidence", 0.6)
        impact = prediction.get("impact", "Moderate impact expected")
        tradeoff = prediction.get("tradeoff", "Balanced risk")
        timeframe = prediction.get("timeframe", "Medium-term")
        context_note = prediction.get("context_note", "Pipeline analysis completed.")

        profile_note = self.build_profile_note(profile)

        decision_brief = {
            "memory_summary": memory_summary,
            "memory_note": memory_note,
            "recommended_move": recommended_move,
            "why_this": self._build_why_this(
                business_understanding,
                dynamic_reasoning,
                market_intelligence
            ),

            "business_understanding": business_understanding,
            "business_dna": business_dna,
            "business_nature": business_understanding.get("business_nature"),
            "market_nature": business_understanding.get("market_nature"),
            "customer_nature": business_understanding.get("customer_nature"),
            "execution_reality": business_understanding.get("execution_reality"),
            "operational_intelligence": operational_intelligence,
"operational_stability": operational_intelligence.get("operational_stability"),
"execution_load": operational_intelligence.get("execution_load"),
"founder_dependency": operational_intelligence.get("founder_dependency"),
"team_pressure": operational_intelligence.get("team_pressure"),
"scalability_risk": operational_intelligence.get("scalability_risk"),
"systemization_score": operational_intelligence.get("systemization_score"),
"main_operational_bottleneck": operational_intelligence.get("main_operational_bottleneck"),
"workflow_risk": operational_intelligence.get("workflow_risk"),
"operational_warning": operational_intelligence.get("operational_warning"),
"recommended_operational_move": operational_intelligence.get("recommended_operational_move"),
"operations_next_steps": operational_intelligence.get("operations_next_steps"),
"scale_readiness": operational_intelligence.get("scale_readiness"),
            "strategic_direction": business_understanding.get("strategic_direction"),

            "dynamic_reasoning": dynamic_reasoning,
            "current_bottleneck": dynamic_reasoning.get("current_bottleneck"),
            "current_priority": dynamic_reasoning.get("current_priority"),
            "execution_focus": dynamic_reasoning.get("execution_focus"),
            "growth_blocker": dynamic_reasoning.get("growth_blocker"),
            "strategic_simulation": pipeline_result.get("strategic_simulation", {}),
            "next_business_evolution": dynamic_reasoning.get("next_business_evolution"),
            "strategic_warning": dynamic_reasoning.get("strategic_warning"),

            "market_pressure": market_intelligence.get("market_pressure"),
            "survival_strategy": market_intelligence.get("survival_strategy"),
            "growth_angle": market_intelligence.get("growth_angle"),
            "premium_insight": market_intelligence.get("premium_insight"),

            "strategy_comparison": strategy_comparison,
            "prediction": prediction,
            "visual_intelligence": visual_intelligence,

            "expected_impact": impact,
            "tradeoff": tradeoff,
            "timeframe": timeframe,
            "confidence": confidence,
            "context_note": context_note,

            "main_risk": dynamic_reasoning.get(
                "strategic_warning",
                self._main_risk_message(best.get("risk", "medium"))
            ),
            "watch_metric": self._watch_metric(business_intent),
            "fallback_move": self._build_fallback(business_intent, dynamic_reasoning, best),
            "profile_note": profile_note,
        }

        advanced_details = {
            "strategy": best.get("name", "Balanced"),
            "risk": best.get("risk", "medium"),
            "business_intent": business_intent,
            "budget": budget,
            "memory_summary": memory_summary,
            "market": market,
            "final_score": best.get("final_score"),
            "decision_score": best.get("decision_score"),
            "trust_score": best.get("trust_score"),
            "failure_probability": best.get("failure_probability"),
            "explanation": explanation or {},
            "profile_note": profile_note,
            "preferences": preferences,
            "pipeline_status": pipeline_result.get("status"),
        }

        return {
            "summary": f"👉 Best move: {recommended_move}",
            "detail": f"For your goal — {clean_goal}",
            "next_steps": next_steps,
            "risk_profile": best.get("risk", "medium"),
            "business_intent": business_intent,
            "caution": self._risk_caution(best.get("risk", "medium")),
            "decision_brief": decision_brief,
            "advanced_details": advanced_details,
        }

    def _build_why_this(self, business_understanding, dynamic_reasoning, market_intelligence):
        business_nature = business_understanding.get(
            "business_nature",
            "AURA analyzed the business structure."
        )

        priority = dynamic_reasoning.get(
            "current_priority",
            "The priority is to validate demand before scaling."
        )

        market_pressure = market_intelligence.get(
            "market_pressure",
            "Market pressure is uncertain, so execution should be controlled."
        )

        return f"{business_nature} {market_pressure} Because of this, the immediate priority is: {priority}"

    def _build_fallback(self, business_intent, dynamic_reasoning, best):
        if dynamic_reasoning.get("strategic_warning"):
            return dynamic_reasoning.get("strategic_warning")

        if business_intent == "online_vs_offline":
            return "If online traction stays weak, shift toward offline trust-building through partnerships, local visibility, or referrals."

        if business_intent == "pricing":
            return "If conversion stays low, customers may not see enough value at the current price."

        if business_intent == "growth":
            return "If growth stalls, focus on one proven acquisition channel instead of many."

        return self._fallback_move(best.get("name", "Balanced"))
    
    def _build_memory_note(self, memory_summary: dict):
        if not memory_summary or not memory_summary.get("has_memory"):
             return "AURA is beginning to build memory for this decision pattern."

        insight = memory_summary.get("memory_insight")

        if insight:
            return insight

        total = memory_summary.get("total_decisions", 0)

        return f"AURA has memory of {total} previous decision(s) in this session."

    def _risk_caution(self, risk: str):
        if risk == "high":
            return "High growth potential, but this needs strong risk control."
        if risk == "low":
            return "Safer path, but growth may be slower."
        return "Balanced path between growth and risk."

    def _main_risk_message(self, risk: str):
        if risk == "high":
            return "You may move too fast before proving real demand."
        if risk == "low":
            return "You may move too slowly and miss opportunities."
        return "Execution uncertainty and weak validation."

    def _watch_metric(self, business_intent: str):
        if business_intent == "pricing":
            return "Conversion rate"
        if business_intent == "growth":
            return "Customer acquisition cost"
        if business_intent == "cost":
            return "Monthly expenses"
        if business_intent == "customer_acquisition":
            return "Lead-to-customer conversion"
        if business_intent == "hiring":
            return "Revenue or output per employee"
        if business_intent == "market_entry":
            return "Early customer demand"
        if business_intent == "online_vs_offline":
            return "Cost per customer"
        return "Customer response"

    def _fallback_move(self, strategy_name: str):
        if strategy_name == "Aggressive":
            return "Slow down and test with a smaller budget."
        if strategy_name == "Conservative":
            return "Try one faster growth channel without risking too much money."
        return "Reduce risk, validate assumptions, and test again."


conversation_engine = ConversationEngine()