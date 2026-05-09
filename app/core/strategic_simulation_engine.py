class StrategicSimulationEngine:

    def simulate(self, goal: str, business_dna: dict, dynamic_reasoning: dict, prediction: dict):
        stage = business_dna.get("business_stage", "unknown_stage")
        model = business_dna.get("business_model", "general_business")
        competition = business_dna.get("competition_pressure", "high")
        trust = business_dna.get("trust_dependency", "medium")
        capital = business_dna.get("capital_intensity", "medium")
        scalability = business_dna.get("scalability", "medium")

        confidence = prediction.get("confidence", 0.6)

        return {
            "simulation_type": "Strategic Simulation V2",
            "business_stage": stage,
            "business_model": model,

            "30_day_projection": self._projection_30(stage, trust, competition),
            "90_day_projection": self._projection_90(stage, scalability, capital),
            "best_case_future": self._best_case(stage, model),
            "most_likely_future": self._most_likely(stage, trust, competition),
            "worst_case_future": self._worst_case(stage, capital, competition),

            "growth_probability": self._growth_probability(confidence, scalability, trust),
            "failure_probability": self._failure_probability(confidence, capital, competition),
            "cash_pressure": self._cash_pressure(capital),
            "trust_growth": self._trust_growth(trust),
            "market_reaction": self._market_reaction(competition),
            "execution_risk": dynamic_reasoning.get(
                "strategic_warning",
                "Execution risk depends on how well the plan is validated before scaling."
            ),

            "recommended_simulated_path": self._recommended_path(stage, trust, capital),
        }

    def _projection_30(self, stage, trust, competition):
        if stage == "early_stage":
            return "The first 30 days should be used for validation, trust-building, and learning from real customer reactions."
        if stage == "growth_stage":
            return "The next 30 days should focus on systemizing what already works before increasing demand."
        if stage == "survival_stage":
            return "The next 30 days should focus on reducing pressure, simplifying operations, and protecting cash."
        return "The next 30 days should clarify positioning and test real demand."

    def _projection_90(self, stage, scalability, capital):
        if stage == "early_stage":
            return "Within 90 days, the business should either prove a repeatable customer signal or pivot the offer."
        if stage == "growth_stage":
            return "Within 90 days, growth may improve if systems, acquisition, and delivery capacity are strengthened."
        if stage == "survival_stage":
            return "Within 90 days, survival depends on stabilizing cash flow and removing weak offers or waste."
        return "Within 90 days, the business should move from uncertainty toward a clearer operating model."

    def _best_case(self, stage, model):
        if model == "digital_product_or_platform":
            return "The best case is fast learning, early proof, improved onboarding, and a repeatable acquisition path."
        if model == "local_repeat_purchase_business":
            return "The best case is repeat customers, strong reviews, and local trust becoming a growth engine."
        if model == "supply_and_distribution_business":
            return "The best case is reliable supplier access, repeat orders, and trust from contractors or business buyers."
        return "The best case is clear positioning, validated demand, and controlled growth."

    def _most_likely(self, stage, trust, competition):
        if trust in ["high", "very_high"]:
            return "The most likely outcome is slow early traction until proof, reviews, or trust signals improve."
        if competition in ["high", "very_high"]:
            return "The most likely outcome is pressure from competitors unless the offer becomes more specific."
        return "The most likely outcome is moderate progress if execution stays focused."

    def _worst_case(self, stage, capital, competition):
        if capital in ["high", "very_high"]:
            return "The worst case is spending too much before demand is proven, creating cash pressure."
        if competition in ["high", "very_high"]:
            return "The worst case is being ignored because customers see no clear reason to choose you."
        return "The worst case is weak validation leading to slow growth and wasted effort."

    def _growth_probability(self, confidence, scalability, trust):
        score = confidence * 100

        if scalability in ["high", "very_high"]:
            score += 10
        if trust in ["high", "very_high"]:
            score -= 5

        if score >= 75:
            return "high"
        if score >= 55:
            return "medium"
        return "low"

    def _failure_probability(self, confidence, capital, competition):
        score = (1 - confidence) * 100

        if capital in ["high", "very_high"]:
            score += 15
        if competition in ["high", "very_high"]:
            score += 10

        if score >= 70:
            return "high"
        if score >= 45:
            return "medium"
        return "low"

    def _cash_pressure(self, capital):
        if capital in ["high", "very_high"]:
            return "High cash pressure: avoid large commitments before demand is proven."
        if capital == "medium":
            return "Moderate cash pressure: test carefully before increasing spend."
        return "Low cash pressure: lean testing is possible."

    def _trust_growth(self, trust):
        if trust in ["high", "very_high"]:
            return "Trust must be built deliberately through proof, reviews, testimonials, guarantees, or visible results."
        return "Trust can grow through clarity, consistency, and customer experience."

    def _market_reaction(self, competition):
        if competition in ["high", "very_high"]:
            return "Competitors may pressure pricing and attention. Differentiation must be clear."
        return "Market reaction may be manageable if the offer reaches the right customer segment."

    def _recommended_path(self, stage, trust, capital):
        if stage == "early_stage":
            return "Validate first, build proof second, scale third."
        if stage == "growth_stage":
            return "Systemize delivery first, increase acquisition second, hire third."
        if stage == "survival_stage":
            return "Protect cash first, simplify the offer second, rebuild demand third."
        return "Clarify the offer first, test demand second, expand only after proof."


strategic_simulation_engine = StrategicSimulationEngine()