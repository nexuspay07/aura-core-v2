from dataclasses import dataclass


@dataclass
class MarketIntelligence:

    market_type: str

    market_maturity: str

    competition_level: str

    growth_rate: str

    disruption_risk: str

    opportunity_score: int

    threat_score: int

    recommended_positioning: str


class MarketIntelligenceEngine:

    MARKET_DATABASE = {

        "ai": {

            "maturity": "high_growth",

            "competition": "very_high",

            "growth_rate": "explosive",

            "disruption_risk": "high",

            "opportunity_score": 95,

            "threat_score": 80,

            "positioning":
                "Differentiate through proprietary intelligence and execution quality"
        },

        "saas": {

            "maturity": "mature",

            "competition": "high",

            "growth_rate": "high",

            "disruption_risk": "medium",

            "opportunity_score": 85,

            "threat_score": 70,

            "positioning":
                "Focus on retention, niche dominance, and recurring revenue"
        },

        "logistics": {

            "maturity": "mature",

            "competition": "high",

            "growth_rate": "medium",

            "disruption_risk": "medium",

            "opportunity_score": 75,

            "threat_score": 65,

            "positioning":
                "Win through operational efficiency and network effects"
        },

        "real_estate": {

            "maturity": "mature",

            "competition": "high",

            "growth_rate": "medium",

            "disruption_risk": "low",

            "opportunity_score": 70,

            "threat_score": 60,

            "positioning":
                "Focus on location advantages and financing structure"
        },

        "healthcare": {

            "maturity": "mature",

            "competition": "medium",

            "growth_rate": "high",

            "disruption_risk": "low",

            "opportunity_score": 85,

            "threat_score": 50,

            "positioning":
                "Build trust, compliance, and long-term customer relationships"
        },

        "finance": {

            "maturity": "mature",

            "competition": "high",

            "growth_rate": "high",

            "disruption_risk": "high",

            "opportunity_score": 90,

            "threat_score": 85,

            "positioning":
                "Create trust and defensible financial infrastructure"
        },

        "general": {

            "maturity": "unknown",

            "competition": "unknown",

            "growth_rate": "unknown",

            "disruption_risk": "unknown",

            "opportunity_score": 50,

            "threat_score": 50,

            "positioning":
                "Validate market conditions before aggressive expansion"
        }
    }

    def detect_market(
        self,
        goal_lower: str
    ):

        if any(
            keyword in goal_lower
            for keyword in [
                "ai",
                "artificial intelligence",
                "machine learning"
            ]
        ):
            return "ai"

        if any(
            keyword in goal_lower
            for keyword in [
                "software",
                "saas",
                "platform"
            ]
        ):
            return "saas"

        if any(
            keyword in goal_lower
            for keyword in [
                "truck",
                "trucking",
                "fleet",
                "shipping",
                "transport",
                "logistics"
            ]
        ):
            return "logistics"

        if any(
            keyword in goal_lower
            for keyword in [
                "property",
                "real estate"
            ]
        ):
            return "real_estate"

        if any(
            keyword in goal_lower
            for keyword in [
                "hospital",
                "clinic",
                "healthcare",
                "medical"
            ]
        ):
            return "healthcare"

        if any(
            keyword in goal_lower
            for keyword in [
                "bank",
                "finance",
                "investment"
            ]
        ):
            return "finance"

        return "general"

    def analyze(
        self,
        goal: str,
        strategic_analysis: dict | None = None
    ):

        goal_lower = goal.lower()

        market_type = (
            self.detect_market(
                goal_lower
            )
        )

        market_data = (
            self.MARKET_DATABASE.get(
                market_type,
                self.MARKET_DATABASE["general"]
            )
        )

        return {

            "market_type":
                market_type,

            "market_maturity":
                market_data["maturity"],

            "competition_level":
                market_data["competition"],

            "growth_rate":
                market_data["growth_rate"],

            "disruption_risk":
                market_data["disruption_risk"],

            "opportunity_score":
                market_data["opportunity_score"],

            "threat_score":
                market_data["threat_score"],

            "recommended_positioning":
                market_data["positioning"]
        }
    
    print(
    "OLD MARKET INTELLIGENCE ENGINE LOADED"
)


market_intelligence_engine = (
    MarketIntelligenceEngine()
)