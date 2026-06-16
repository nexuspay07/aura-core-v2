from dataclasses import dataclass


@dataclass
class StrategicAnalysis:

    business_stage: str
    business_model: str

    primary_objective: str
    decision_type: str

    time_horizon: str

    urgency: str

    risk_profile: str

    capital_requirement: str

    execution_complexity: str

    growth_phase: str


class StrategicAnalysisEngine:

    OBJECTIVE_KEYWORDS = {

        "customer_acquisition": [
            "customer",
            "customers",
            "client",
            "clients",
            "lead",
            "sales",
            "prospect"
        ],

        "revenue_growth": [
            "revenue",
            "profit",
            "income",
            "grow revenue",
            "increase revenue"
        ],

        "fundraising": [
            "investor",
            "investors",
            "raise capital",
            "raise money",
            "venture capital",
            "angel investor",
            "seed round",
            "series a",
            "fundraising"
        ],

        "market_expansion": [
            "expand",
            "expansion",
            "international",
            "global",
            "europe",
            "africa",
            "asia",
            "new market"
        ],

        "merger_acquisition": [
            "acquire",
            "acquisition",
            "buy company",
            "buy business",
            "purchase company",
            "purchase business",
            "merger",
            "takeover"
        ],

        "partnerships": [
            "partner",
            "partnership",
            "alliance",
            "joint venture"
        ],

        "pricing_strategy": [
            "pricing",
            "price",
            "subscription",
            "pricing model"
        ],

        "cost_reduction": [
            "reduce costs",
            "cut costs",
            "save money",
            "expenses",
            "efficiency"
        ],

        "operational_efficiency": [
            "operations",
            "workflow",
            "process",
            "automation",
            "optimize"
        ],

        "product_strategy": [
            "product",
            "feature",
            "roadmap",
            "launch"
        ],

        "competitive_positioning": [
            "competitor",
            "competition",
            "market share",
            "positioning"
        ]
    }

    BUSINESS_MODEL_KEYWORDS = {

        "saas": [
            "saas",
            "software",
            "ai",
            "platform"
        ],

        "marketplace": [
            "marketplace"
        ],

        "ecommerce": [
            "ecommerce",
            "online store",
            "shopify"
        ],

        "restaurant": [
            "restaurant",
            "food"
        ],

        "real_estate": [
            "real estate",
            "property"
        ],

        "logistics": [
            "trucking",
            "transport",
            "logistics",
            "shipping",
            "fleet"
        ],

        "manufacturing": [
            "manufacturing",
            "factory",
            "production"
        ],

        "healthcare": [
            "hospital",
            "clinic",
            "medical",
            "healthcare"
        ],

        "finance": [
            "bank",
            "finance",
            "financial",
            "investment"
        ]
    }

    def detect_objective(
        self,
        goal_lower: str
    ):

        scores = {}

        for objective, keywords in (
            self.OBJECTIVE_KEYWORDS.items()
        ):

            score = 0

            for keyword in keywords:

                if keyword in goal_lower:
                    score += 1

            scores[objective] = score

        best_match = max(
            scores,
            key=scores.get
        )

        if scores[best_match] == 0:
            return "general_strategy"

        return best_match

    def detect_business_model(
        self,
        goal_lower: str
    ):

        scores = {}

        for model, keywords in (
            self.BUSINESS_MODEL_KEYWORDS.items()
        ):

            score = 0

            for keyword in keywords:

                if keyword in goal_lower:
                    score += 1

            scores[model] = score

        best_match = max(
            scores,
            key=scores.get
        )

        if scores[best_match] == 0:
            return "unknown"

        return best_match

    def analyze(
        self,
        goal: str,
        profile: dict | None = None
    ):

        goal_lower = goal.lower()

        objective = (
            self.detect_objective(
                goal_lower
            )
        )

        business_model = (
            self.detect_business_model(
                goal_lower
            )
        )

        business_stage = "early_stage"

        if (
            "first customer" in goal_lower
            or "first 10" in goal_lower
        ):
            business_stage = "validation"

        elif "scale" in goal_lower:
            business_stage = "growth"

        elif (
            "expand" in goal_lower
            or "international" in goal_lower
        ):
            business_stage = "expansion"

        decision_map = {

            "customer_acquisition":
                "sales",

            "revenue_growth":
                "finance",

            "fundraising":
                "finance",

            "market_expansion":
                "growth",

            "merger_acquisition":
                "acquisition",

            "partnerships":
                "partnership",

            "pricing_strategy":
                "finance",

            "cost_reduction":
                "operations",

            "operational_efficiency":
                "operations",

            "product_strategy":
                "product",

            "competitive_positioning":
                "strategy"
        }

        decision_type = (
            decision_map.get(
                objective,
                "strategy"
            )
        )

        time_horizon = "medium_term"

        if any(
            keyword in goal_lower
            for keyword in [
                "first",
                "immediately",
                "urgent",
                "now"
            ]
        ):
            time_horizon = "short_term"

        elif any(
            keyword in goal_lower
            for keyword in [
                "5 years",
                "10 years",
                "long term"
            ]
        ):
            time_horizon = "long_term"

        risk_profile = "medium"

        if objective in [
            "fundraising",
            "merger_acquisition"
        ]:
            risk_profile = "high"

        capital_requirement = "low"

        if objective in [
            "fundraising",
            "market_expansion",
            "merger_acquisition"
        ]:
            capital_requirement = "high"

        execution_complexity = "moderate"

        if objective in [
            "market_expansion",
            "merger_acquisition"
        ]:
            execution_complexity = "high"

        growth_phase = business_stage

        urgency = "medium"

        if any(
            keyword in goal_lower
            for keyword in [
                "urgent",
                "immediately",
                "now"
            ]
        ):
            urgency = "high"

        confidence_score = 0.50

        if objective != "general_strategy":
            confidence_score += 0.20

        if business_model != "unknown":
            confidence_score += 0.20

        if decision_type != "strategy":
            confidence_score += 0.10

        return {

            "business_stage":
                business_stage,

            "business_model":
                business_model,

            "primary_objective":
                objective,

            "decision_type":
                decision_type,

            "time_horizon":
                time_horizon,

            "urgency":
                urgency,

            "risk_profile":
                risk_profile,

            "capital_requirement":
                capital_requirement,

            "execution_complexity":
                execution_complexity,

            "growth_phase":
                growth_phase,

            "confidence_score":
                confidence_score
        }


strategic_analysis_engine = (
    StrategicAnalysisEngine()
)