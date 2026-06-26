import re


class BusinessUnderstandingEngine:
    """
    Universal Business Understanding Engine

    This does NOT depend on fixed business categories only.
    It reads the user's goal and builds a flexible "business DNA"
    that other AURA engines can reason from.
    """

    

    def analyze(
        self,
        goal: str,
        scenario: dict | None = None,
        strategic_analysis: dict | None = None,
        market_intelligence: dict | None = None,
        competitive_intelligence: dict | None = None,
    ):
        scenario = scenario or {}
        strategic_analysis = strategic_analysis or {}
        market_intelligence = market_intelligence or {}
        competitive_intelligence = competitive_intelligence or {}
        text = goal.lower()

        budget = scenario.get("budget") or self._extract_budget(text) or 10000
        market = scenario.get("market") or self._detect_market(text)
        business_model = self._detect_business_model(text)
        customer_type = self._detect_customer_type(text)
        channel = self._detect_channel(text)
        stage = self._detect_stage(text)

        dna = {
            "business_model": business_model,
            "customer_type": customer_type,
            "primary_channel": channel,
            "business_stage": stage,
            "budget": budget,
            "market": market,
            "trust_dependency": self._score_trust_dependency(text, business_model),
            "repeat_purchase_potential": self._score_repeat_purchase(
                text, business_model
            ),
            "capital_intensity": self._score_capital_intensity(
                text, business_model, channel
            ),
            "operational_complexity": self._score_operational_complexity(
                text, business_model
            ),
            "competition_pressure": self._score_competition_pressure(text, market),
            "customer_emotion": self._score_customer_emotion(text, business_model),
            "price_sensitivity": self._score_price_sensitivity(text),
            "scalability": self._score_scalability(text, business_model, channel),
            "proof_requirement": self._score_proof_requirement(text, business_model),
            "speed_importance": self._score_speed_importance(text, market),
            "location_dependency": self._score_location_dependency(text, channel),
            "brand_importance": self._score_brand_importance(text, business_model),
        }

        executive_context = self._build_executive_context(
            strategic_analysis, market_intelligence, competitive_intelligence
        )

        return {
            "business_dna": dna,
            "executive_context": executive_context,
            "business_nature": self._describe_business_nature(dna),
            "market_nature": self._describe_market_nature(dna),
            "customer_nature": self._describe_customer_nature(dna),
            "execution_reality": self._describe_execution_reality(dna),
            "strategic_direction": self._strategic_direction(dna, executive_context),
        }

    def _extract_budget(self, text: str):
        match = re.search(r"\$?\s?(\d{3,9})", text)
        if match:
            return int(match.group(1))

        if any(
            x in text
            for x in ["low budget", "small budget", "limited budget", "little money"]
        ):
            return 3000

        if any(x in text for x in ["medium budget", "average budget"]):
            return 10000

        if any(x in text for x in ["high budget", "large budget", "big budget"]):
            return 50000

        return None

    def _detect_market(self, text: str):
        if any(
            x in text
            for x in [
                "competitive",
                "competition",
                "crowded",
                "saturated",
                "many competitors",
                "bigger competitors",
                "similar businesses",
                "many businesses",
                "lots of competition",
            ]
        ):
            return "competitive"

        if any(
            x in text
            for x in [
                "few competitors",
                "not many competitors",
                "low competition",
                "no competition",
                "new market",
            ]
        ):
            return "less_competitive"

        return "uncertain"

    def _detect_business_model(self, text: str):
        if any(
            x in text
            for x in ["restaurant", "food", "cafe", "bakery", "pizza", "shawarma"]
        ):
            return "local_repeat_purchase_business"

        if any(
            x in text
            for x in ["software", "saas", "app", "platform", "ai tool", "automation"]
        ):
            return "digital_product_or_platform"

        if any(
            x in text
            for x in ["agency", "consulting", "service", "freelance", "marketing"]
        ):
            return "service_business"

        if any(
            x in text
            for x in ["clothing", "fashion", "brand", "sneaker", "beauty", "cosmetic"]
        ):
            return "brand_driven_product_business"

        if any(
            x in text
            for x in [
                "building material",
                "construction",
                "cement",
                "tiles",
                "hardware",
            ]
        ):
            return "supply_and_distribution_business"

        if any(
            x in text for x in ["course", "tutor", "training", "education", "coaching"]
        ):
            return "knowledge_business"

        if any(
            x in text
            for x in [
                "store",
                "shop",
                "retail",
                "sell products",
                "ecommerce",
                "online store",
            ]
        ):
            return "retail_or_ecommerce_business"

        if any(
            x in text for x in ["holding company", "conglomerate", "group", "portfolio"]
        ):
            return "holding_company"

        if any(
            x in text for x in ["fintech", "payments", "banking", "wallet", "nexuspay"]
        ):
            return "financial_platform"

        if any(
            x in text
            for x in ["artificial intelligence", "ai", "automation platform", "aura ai"]
        ):
            return "ai_platform"

        return "general_business"

    def _detect_customer_type(self, text: str):
        if any(
            x in text
            for x in ["contractor", "builders", "companies", "businesses", "b2b"]
        ):
            return "business_customers"

        if any(x in text for x in ["students", "parents", "families"]):
            return "specialized_consumers"

        if any(
            x in text for x in ["customers", "people", "users", "buyers", "clients"]
        ):
            return "general_consumers"

        return "unknown_customers"

    def _detect_channel(self, text: str):
        has_online = any(
            x in text for x in ["online", "website", "app", "social media", "ecommerce"]
        )
        has_offline = any(
            x in text for x in ["offline", "physical", "store", "shop", "location"]
        )

        if has_online and has_offline:
            return "hybrid_online_offline"

        if has_online:
            return "online"

        if has_offline:
            return "offline"

        return "unknown_channel"

    def _detect_stage(self, text: str):
        if any(
            x in text
            for x in ["start", "starting", "open", "launch", "idea", "new business"]
        ):
            return "early_stage"

        if any(
            x in text for x in ["grow", "scale", "more customers", "increase sales"]
        ):
            return "growth_stage"

        if any(
            x in text
            for x in ["struggling", "losing money", "not selling", "low sales"]
        ):
            return "survival_stage"

        return "unknown_stage"

    def _level(self, score: int):
        if score >= 80:
            return "very_high"
        if score >= 60:
            return "high"
        if score >= 40:
            return "medium"
        if score >= 20:
            return "low"
        return "very_low"

    def _score_trust_dependency(self, text, model):
        score = 40

        if model in [
            "service_business",
            "supply_and_distribution_business",
            "knowledge_business",
            "digital_product_or_platform",
        ]:
            score += 30

        if any(
            x in text
            for x in [
                "expensive",
                "health",
                "money",
                "contractor",
                "businesses",
                "clients",
            ]
        ):
            score += 20

        return self._level(min(score, 100))

    def _score_repeat_purchase(self, text, model):
        if model == "local_repeat_purchase_business":
            return "very_high"

        if model in [
            "service_business",
            "supply_and_distribution_business",
            "knowledge_business",
        ]:
            return "high"

        if model == "brand_driven_product_business":
            return "medium"

        return "medium"

    def _score_capital_intensity(self, text, model, channel):
        score = 35

        if channel == "offline":
            score += 30

        if model in [
            "local_repeat_purchase_business",
            "supply_and_distribution_business",
        ]:
            score += 25

        if any(
            x in text for x in ["inventory", "rent", "equipment", "warehouse", "store"]
        ):
            score += 20

        return self._level(min(score, 100))

    def _score_operational_complexity(self, text, model):
        score = 40

        if model in [
            "local_repeat_purchase_business",
            "supply_and_distribution_business",
        ]:
            score += 30

        if model == "digital_product_or_platform":
            score += 20

        if any(
            x in text
            for x in ["delivery", "inventory", "employees", "hiring", "supplier"]
        ):
            score += 20

        return self._level(min(score, 100))

    def _score_competition_pressure(self, text, market):
        if market == "competitive":
            return "very_high"

        if market == "less_competitive":
            return "medium"

        return "high"

    def _score_customer_emotion(self, text, model):
        if model in ["brand_driven_product_business", "local_repeat_purchase_business"]:
            return "high"

        if model == "knowledge_business":
            return "medium"

        return "medium"

    def _score_price_sensitivity(self, text):
        if any(
            x in text
            for x in [
                "cheap",
                "low price",
                "price sensitive",
                "affordable",
                "budget customers",
            ]
        ):
            return "very_high"

        if any(x in text for x in ["premium", "luxury", "high-end"]):
            return "medium"

        return "high"

    def _score_scalability(self, text, model, channel):
        if model == "digital_product_or_platform":
            return "very_high"

        if channel == "online":
            return "high"

        if model == "service_business":
            return "medium"

        if model == "local_repeat_purchase_business":
            return "medium"

        return "medium"

    def _score_proof_requirement(self, text, model):
        if model in [
            "service_business",
            "knowledge_business",
            "supply_and_distribution_business",
            "digital_product_or_platform",
        ]:
            return "very_high"

        return "high"

    def _score_speed_importance(self, text, market):
        if market == "competitive":
            return "very_high"

        return "high"

    def _score_location_dependency(self, text, channel):
        if channel == "offline":
            return "high"

        if channel == "hybrid_online_offline":
            return "medium"

        return "low"

    def _score_brand_importance(self, text, model):
        if model == "brand_driven_product_business":
            return "very_high"

        if model in ["local_repeat_purchase_business", "digital_product_or_platform"]:
            return "high"

        return "medium"

    def _describe_business_nature(self, dna):
        model = dna["business_model"]

        if model == "local_repeat_purchase_business":
            return "This business depends on repeat customers, local trust, consistency, and customer experience."

        if model == "digital_product_or_platform":
            return "This business depends on solving a clear problem, fast iteration, onboarding, and user retention."

        if model == "supply_and_distribution_business":
            return "This business depends on supplier reliability, stock availability, delivery speed, and trust."

        if model == "brand_driven_product_business":
            return "This business depends on perception, identity, trust, visuals, and customer loyalty."

        if model == "service_business":
            return "This business depends on trust, proof, communication, delivery quality, and client relationships."

        return "This business depends on clear positioning, customer trust, value delivery, and disciplined execution."

    def _describe_market_nature(self, dna):
        if dna["competition_pressure"] in ["very_high", "high"]:
            return "The market is pressure-heavy. Customers already have options, so unclear offers will be ignored."

        return "The market may offer room to enter, but demand still needs to be validated before scaling."

    def _describe_customer_nature(self, dna):
        if dna["trust_dependency"] in ["very_high", "high"]:
            return "Customers need proof before they act. Trust, reviews, clarity, and low-risk offers matter."

        return "Customers need a simple reason to care, understand, and try the offer."

    def _describe_execution_reality(self, dna):
        if dna["capital_intensity"] in ["very_high", "high"]:
            return "Execution requires cash discipline. Spending too early can create pressure before demand is proven."

        return "Execution can start lean. The priority is learning quickly before increasing spend."

    def _strategic_direction(
        self,
        dna,
        executive_context
        ):

        industry = executive_context.get(
            "industry",
            "unknown"
        )

        objective = executive_context.get(
            "objective",
            "general_strategy"
        )

        moat = executive_context.get(
            "strategic_moat",
            "unknown"
        )

        competition = executive_context.get(
            "competition",
            "unknown"
        )

        if objective == "merger_acquisition":
            return (
                f"Evaluate acquisition targets "
                f"based on operational leverage, "
                f"cash flow quality, market share, "
                f"and defensible advantages. "
                f"The primary competitive moat "
                f"in this industry is {moat}."
            )

        if objective == "market_expansion":
            return (
                "Prioritize expansion markets "
                "where competitive intensity "
                "is manageable and execution "
                "advantages can be replicated."
            )

        if objective == "fundraising":
            return (
                "Build investor confidence "
                "through traction, execution "
                "evidence, and scalable economics."
            )

        if industry == "logistics":
            return (
                f"The logistics sector rewards "
                f"network density, operational "
                f"efficiency, and asset utilization. "
                f"Competition level is "
                f"{competition}. Focus on "
                f"route optimization and "
                f"contract quality."
            )

        if industry == "ai":
            return (
                "Create proprietary intelligence, "
                "data advantages, and superior "
                "execution."
            )

        if dna["business_model"] == "holding_company":
            return (
                "Concentrate resources into the "
                "strongest subsidiary until "
                "sustainable cash flow exists."
            )

        if dna["business_model"] == "financial_platform":
            return (
                "Trust, compliance, and transaction "
                "reliability should be established "
                "before aggressive growth."
            )

        if dna["business_model"] == "ai_platform":
            return (
                "Create a defensible intelligence "
                "advantage before scaling."
            )

        return (
            "Strengthen market position, "
            "improve execution quality, "
            "and scale only after proven demand."
        )

    def _build_executive_context(
        self,
        strategic_analysis,
        market_intelligence,
        competitive_intelligence
    ):

        return {

            "industry":
                strategic_analysis.get(
                    "business_model",
                    "unknown"
                ),

            "objective":
                strategic_analysis.get(
                    "primary_objective",
                    "general_strategy"
                ),

            "market_growth":
                market_intelligence.get(
                    "growth_rate",
                    "unknown"
                ),

            "competition":
                competitive_intelligence.get(
                    "competition_intensity",
                    "unknown"
                ),

            "strategic_moat":
                competitive_intelligence.get(
                    "recommended_moat",
                    "unknown"
                )
        }
    
business_understanding_engine = (
    BusinessUnderstandingEngine()
)
