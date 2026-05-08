import re

from app.domains.business.business_domain_engine import business_domain_engine
from app.domains.business.business_strategy_engine import business_strategy_engine
from app.core.prediction_engine import prediction_engine, get_market_context
from app.core.strategy_comparison_engine import strategy_comparison_engine
from app.core.market_intelligence_engine import market_intelligence_engine
from app.core.decision_depth_engine import decision_depth_engine
from app.core.reality_engine import reality_engine
from app.core.adaptive_intelligence_engine import adaptive_intelligence_engine


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
        "competitive",
        "competition",
        "crowded",
        "saturated",
        "many competitors",
        "lots of competition",
        "too many businesses",
        "many businesses",
        "many similar businesses",
        "similar businesses",
        "similar business",
        "bigger competitors",
        "big competitors",
        "larger competitors",
        "established competitors",
        "other businesses like mine",
        "people doing the same thing",
        "stores like mine",
        "companies like mine"
    ]):
        market = "competitive"

    elif any(x in m for x in [
        "few competitors",
        "not many competitors",
        "not many businesses",
        "less crowded",
        "low competition",
        "no competition",
        "new market",
        "monopoly"
    ]):
        market = "monopoly"

    return {
        "budget": budget,
        "market": market
    }


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

        if any(x in m for x in [
            "invest", "money", "portfolio", "budget", "finance", "returns"
        ]):
            return "finance_strategy"

        return "general"

    def missing_context(self, preferences: dict):
        missing = []

        if not preferences.get("budget"):
            missing.append("budget")

        if not preferences.get("market"):
            missing.append("market")

        return missing

    def build_context_question(self, missing: list):
        questions = []

        if "budget" in missing:
            questions.append(
                "What is your budget? Example: $1000, $3000, $5000, or low/medium/high."
            )

        if "market" in missing:
            questions.append(
                "How crowded is your market? Example: many similar businesses, few competitors, or not sure."
            )

        return "To give you a better decision, I need:\n\n• " + "\n• ".join(questions)

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

        prefixes = [
            "I want to ",
            "i want to ",
            "I need to ",
            "i need to ",
            "I would like to ",
            "i would like to ",
        ]

        for prefix in prefixes:
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
        explanation: list,
        profile: dict | None = None
    ):
        profile = profile or {}

        name = best.get("name", "Balanced")
        risk = best.get("risk", "medium")
        clean_goal = self.clean_goal_text(goal)

        business_intent = business_domain_engine.detect_subdomain(goal)
        print("[AURA INTENT]", business_intent)

        preferences = self.extract_preferences(goal)

        if preferences.get("budget"):
            profile["budget"] = preferences["budget"]

        if preferences.get("market"):
            profile["market"] = preferences["market"]

        budget = preferences.get("budget")
        market = preferences.get("market")

        missing = self.missing_context(preferences)

        if missing:
            if not budget:
                budget = profile.get("preferred_budget") or 10000

            if not market:
                market = profile.get("market") or "competitive"

            preferences["budget"] = budget
            preferences["market"] = market

        market_context = get_market_context()

        market_intelligence = market_intelligence_engine.analyze(
            business_intent,
            {
                "budget": budget,
                "market": market,
                "risk": risk
            }
        )

        decision_depth = decision_depth_engine.analyze(
            business_intent,
            {
                "budget": budget,
                "market": market,
                "risk": risk
            }
        )

        reality = reality_engine.analyze(
            business_intent,
            {
                "budget": budget,
                "market": market,
                "risk": risk
            }
        )

        adaptive = adaptive_intelligence_engine.analyze(
            goal,
            {
                "budget": budget,
                "market": market,
                "risk": risk
            }
        )

        business_strategy = business_strategy_engine.generate_strategy(
            business_intent,
            {
                "goal": goal,
                "risk": risk,
                "strategy": name,
                "budget": budget,
                "market": market
            }
        )

        prediction = prediction_engine.predict_outcome(
            business_intent,
            name,
            {
                "risk": risk,
                "budget": budget,
                "market": market
            }
        )

        strategy_comparison = strategy_comparison_engine.compare(
            business_intent,
            {
                "risk": risk,
                "budget": budget,
                "market": market
            }
        )

        next_steps = business_strategy.get("steps", [
            "Start small",
            "Measure results",
            "Scale if it works"
        ])

        best_move = next_steps[0] if next_steps else "Start with a small test"

        confidence = prediction.get("confidence", 0.6)
        impact = prediction.get("impact", "Moderate impact expected")
        tradeoff = prediction.get("tradeoff", "Balanced risk")
        timeframe = prediction.get("timeframe", "Medium-term")
        context_note = prediction.get("context_note", "General estimate")

        # IMPORTANT:
        # This now uses the actual goal-specific strategy instead of forcing
        # the same static competitive-market answer every time.
        recommended_move = business_strategy.get("advice", best_move)

        if business_intent == "online_vs_offline":
            fallback = (
                "If online traction stays weak after testing, shift toward local offline trust-building "
                "such as partnerships, physical visibility, or direct referrals."
            )

        elif business_intent == "restaurant_strategy":
            fallback = (
                "If repeat orders stay low, improve taste consistency, speed, pricing, or customer experience."
            )

        elif business_intent == "building_materials":
            fallback = (
                "If contractors do not return, improve delivery speed, stock reliability, or trust."
            )

        elif business_intent == "pricing":
            fallback = (
                "If conversion stays low, customers may not see enough value at the current price."
            )

        elif business_intent == "growth":
            fallback = (
                "If growth stalls, focus on one customer acquisition channel instead of many."
            )

        else:
            fallback = self._fallback_move(name)

        profile_note = self.build_profile_note(profile)

        decision_brief = {
            "market_pressure": market_intelligence.get("market_pressure"),
            "survival_strategy": market_intelligence.get("survival_strategy"),
            "growth_angle": market_intelligence.get("growth_angle"),
            "premium_insight": market_intelligence.get("premium_insight"),

            "reality_check": reality.get("reality_check"),
            "brutal_truth": reality.get("brutal_truth"),
            "why_not_aggressive": reality.get("why_not_aggressive"),
            "why_not_balanced": reality.get("why_not_balanced"),
            "why_this_strategy_wins": reality.get("why_this_strategy_wins"),

            "adaptive_intelligence": adaptive,
            "industry": adaptive.get("industry"),
            "business_stage": adaptive.get("business_stage"),
            "customer_psychology": adaptive.get("customer_psychology"),
            "dominant_advantage": adaptive.get("dominant_advantage"),
            "execution_style": adaptive.get("execution_style"),
            "growth_style": adaptive.get("growth_style"),
            "communication_strategy": adaptive.get("communication_strategy"),
            "avoid_this": adaptive.get("avoid_this"),

            "personalized_reality": decision_depth.get("personalized_reality"),
            "competitor_threat": decision_depth.get("competitor_threat"),
            "hidden_opportunity": decision_depth.get("hidden_opportunity"),

            "expected_impact": impact,
            "tradeoff": tradeoff,
            "timeframe": timeframe,
            "confidence": confidence,
            "strategy_comparison": strategy_comparison,
            "recommended_move": recommended_move,
            "context_note": context_note,
            "why_this": (
                f"AURA selected this recommendation because it matches the specific goal, "
                f"budget, market condition, risk level, and predicted outcome strength."
            ),
            "profile_note": profile_note,
            "market_context": (
                f"Current market shows {market_context.get('economy', 'uncertain conditions')} with "
                f"{market_context.get('consumer_behavior', 'changing')} consumers. "
                f"Businesses must focus on value, efficiency, and survival strategies."
            ),
            "main_risk": self._main_risk_message(risk),
            "watch_metric": self._watch_metric(business_intent),
            "fallback_move": fallback
        }

        advanced_details = {
            "strategy": name,
            "risk": risk,
            "business_intent": business_intent,
            "budget": budget,
            "market": market,
            "final_score": best.get("final_score"),
            "decision_score": best.get("decision_score"),
            "trust_score": best.get("trust_score"),
            "failure_probability": best.get("failure_probability"),
            "explanation": explanation or [],
            "profile_note": profile_note,
            "preferences": preferences,
        }

        return {
            "summary": f"👉 Best move: {recommended_move}",
            "detail": f"For your goal — {clean_goal}",
            "next_steps": next_steps,
            "risk_profile": risk,
            "business_intent": business_intent,
            "caution": self._risk_caution(risk),
            "decision_brief": decision_brief,
            "advanced_details": advanced_details,
        }

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

        if business_intent == "restaurant_strategy":
            return "Repeat order rate"

        if business_intent == "building_materials":
            return "Repeat contractor orders"

        return "Customer response"

    def _fallback_move(self, strategy_name: str):
        if strategy_name == "Aggressive":
            return "Slow down and test with a smaller budget."

        if strategy_name == "Conservative":
            return "Try one faster growth channel without risking too much money."

        return "Reduce risk, validate assumptions, and test again."


conversation_engine = ConversationEngine()