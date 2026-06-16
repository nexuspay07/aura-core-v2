from dataclasses import dataclass


@dataclass
class CompetitiveIntelligence:

    competition_intensity: str

    market_saturation: str

    barrier_to_entry: str

    customer_switching_cost: str

    differentiation_requirement: str

    competitive_advantage: str

    competitive_risk: str

    recommended_moat: str


class CompetitiveIntelligenceEngine:

    INDUSTRY_COMPETITION = {

        "ai": {

            "competition_intensity":
                "extreme",

            "market_saturation":
                "high",

            "barrier_to_entry":
                "medium",

            "switching_cost":
                "low",

            "differentiation":
                "critical",

            "advantage":
                "speed_of_innovation",

            "risk":
                "rapid_displacement",

            "moat":
                "proprietary_data"
        },

        "saas": {

            "competition_intensity":
                "high",

            "market_saturation":
                "high",

            "barrier_to_entry":
                "medium",

            "switching_cost":
                "medium",

            "differentiation":
                "critical",

            "advantage":
                "customer_retention",

            "risk":
                "commodity_features",

            "moat":
                "ecosystem_lockin"
        },

        "logistics": {

            "competition_intensity":
                "high",

            "market_saturation":
                "mature",

            "barrier_to_entry":
                "high",

            "switching_cost":
                "medium",

            "differentiation":
                "important",

            "advantage":
                "operational_efficiency",

            "risk":
                "margin_compression",

            "moat":
                "distribution_network"
        },

        "finance": {

            "competition_intensity":
                "high",

            "market_saturation":
                "high",

            "barrier_to_entry":
                "very_high",

            "switching_cost":
                "high",

            "differentiation":
                "trust",

            "advantage":
                "credibility",

            "risk":
                "regulatory_pressure",

            "moat":
                "licenses_and_trust"
        },

        "healthcare": {

            "competition_intensity":
                "medium",

            "market_saturation":
                "medium",

            "barrier_to_entry":
                "very_high",

            "switching_cost":
                "high",

            "differentiation":
                "trust",

            "advantage":
                "patient_relationships",

            "risk":
                "compliance_cost",

            "moat":
                "reputation"
        },

        "general": {

            "competition_intensity":
                "medium",

            "market_saturation":
                "medium",

            "barrier_to_entry":
                "medium",

            "switching_cost":
                "medium",

            "differentiation":
                "important",

            "advantage":
                "execution",

            "risk":
                "competition",

            "moat":
                "customer_loyalty"
        }
    }

    def analyze(
        self,
        strategic_analysis: dict,
        market_intelligence: dict
    ):

        industry = (
            strategic_analysis.get(
                "business_model",
                "general"
            )
        )

        data = (
            self.INDUSTRY_COMPETITION.get(
                industry,
                self.INDUSTRY_COMPETITION[
                    "general"
                ]
            )
        )

        return {

            "competition_intensity":
                data[
                    "competition_intensity"
                ],

            "market_saturation":
                data[
                    "market_saturation"
                ],

            "barrier_to_entry":
                data[
                    "barrier_to_entry"
                ],

            "customer_switching_cost":
                data[
                    "switching_cost"
                ],

            "differentiation_requirement":
                data[
                    "differentiation"
                ],

            "competitive_advantage":
                data[
                    "advantage"
                ],

            "competitive_risk":
                data[
                    "risk"
                ],

            "recommended_moat":
                data[
                    "moat"
                ]
        }


competitive_intelligence_engine = (
    CompetitiveIntelligenceEngine()
)