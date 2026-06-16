class StrategicAnalysisEngine:

    def analyze(
        self,
        goal: str,
        profile: dict | None = None
    ):

        goal_lower = goal.lower()

        business_stage = "unknown"
        objective = "unknown"

        if any(
            word in goal_lower
            for word in [
                "first customer",
                "first 10",
                "first 100",
                "startup",
                "launch"
            ]
        ):
            business_stage = "early-stage"

        elif any(
            word in goal_lower
            for word in [
                "scale",
                "grow",
                "expand"
            ]
        ):
            business_stage = "growth-stage"

        elif any(
            word in goal_lower
            for word in [
                "global",
                "enterprise",
                "international"
            ]
        ):
            business_stage = "expansion-stage"

        # ---------------------------------
        # Objective Detection
        # ---------------------------------

        if any(
            word in goal_lower
            for word in [
                "customer",
                "users",
                "acquire"
            ]
        ):
            objective = "customer_acquisition"

        elif any(
            word in goal_lower
            for word in [
                "revenue",
                "sales",
                "profit"
            ]
        ):
            objective = "revenue_growth"

        elif any(
            word in goal_lower
            for word in [
                "launch",
                "beta",
                "product"
            ]
        ):
            objective = "product_launch"

        # ---------------------------------
        # Strategic Assessment
        # ---------------------------------

        strength = (
            "AI-powered platform"
        )

        weakness = (
            "Limited market validation"
        )

        opportunity = (
            "Growing AI adoption"
        )

        threat = (
            "Strong competition"
        )

        recommended_focus = (
            "Validate demand before scaling"
        )

        if objective == "customer_acquisition":

            recommended_focus = (
                "Founder-led sales and direct outreach"
            )

        elif objective == "product_launch":

            recommended_focus = (
                "Private beta and customer validation"
            )

        elif objective == "revenue_growth":

            recommended_focus = (
                "Increase conversion rates before expansion"
            )

        return {

            "business_stage":
                business_stage,

            "objective":
                objective,

            "strength":
                strength,

            "weakness":
                weakness,

            "opportunity":
                opportunity,

            "threat":
                threat,

            "recommended_focus":
                recommended_focus
        }


strategic_analysis_engine = (
    StrategicAnalysisEngine()
)