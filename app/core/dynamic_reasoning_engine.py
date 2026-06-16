from dataclasses import dataclass


@dataclass
class DynamicReasoning:

    current_priority: str

    execution_focus: str

    growth_blocker: str

    next_business_evolution: str

    strategic_warning: str

    executive_summary: str


class DynamicReasoningEngine:

    def analyze(
        self,
        strategic_analysis: dict,
        market_intelligence: dict,
        competitive_intelligence: dict,
        business_understanding: dict
    ):

        objective = strategic_analysis.get(
            "primary_objective",
            "general_strategy"
        )

        industry = market_intelligence.get(
            "market_type",
            "general"
        )

        competition = market_intelligence.get(
            "competition_level",
            "unknown"
        )

        moat = competitive_intelligence.get(
            "recommended_moat",
            "differentiation"
        )

        strategic_direction = business_understanding.get(
            "strategic_direction",
            ""
        )

        # ==========================================
        # MERGER / ACQUISITION
        # ==========================================

        if objective == "merger_acquisition":

            return {

                "current_priority":
                    "Validate acquisition economics before committing capital.",

                "execution_focus":
                    "Assess operating margins, cash flows, customer concentration, integration complexity, and asset quality.",

                "growth_blocker":
                    "Overestimating synergies or acquiring low-performing assets.",

                "next_business_evolution":
                    "Expand through disciplined acquisition and integration capabilities.",

                "strategic_warning":
                    "Acquisitions destroy value when integration risk exceeds operational upside.",

                "executive_summary":
                    "Treat acquisitions as strategic capability investments rather than shortcuts to growth."
            }

        # ==========================================
        # FUNDRAISING
        # ==========================================

        if objective == "fundraising":

            return {

                "current_priority":
                    "Demonstrate investable traction.",

                "execution_focus":
                    "Strengthen revenue consistency, customer retention, growth metrics, and investor narrative.",

                "growth_blocker":
                    "Attempting to raise capital before proving product-market fit.",

                "next_business_evolution":
                    "Transition from founder-led growth to institutional scale.",

                "strategic_warning":
                    "Premature fundraising increases dilution and weakens negotiating power.",

                "executive_summary":
                    "Investors fund evidence, not ambition."
            }

        # ==========================================
        # MARKET EXPANSION
        # ==========================================

        if objective == "market_expansion":

            return {

                "current_priority":
                    "Validate target-market attractiveness.",

                "execution_focus":
                    "Study local competition, regulations, customer behavior, and distribution channels.",

                "growth_blocker":
                    "Entering markets without a clear advantage.",

                "next_business_evolution":
                    "Develop repeatable international expansion systems.",

                "strategic_warning":
                    "Scaling weaknesses across new markets magnifies failure.",

                "executive_summary":
                    "Expand only after identifying a defensible path to winning."
            }

        # ==========================================
        # REVENUE GROWTH
        # ==========================================

        if objective == "revenue_growth":

            return {

                "current_priority":
                    "Increase revenue quality and efficiency.",

                "execution_focus":
                    "Improve pricing, customer retention, monetization, and unit economics.",

                "growth_blocker":
                    "Growing unprofitable revenue streams.",

                "next_business_evolution":
                    "Shift toward higher-value customers and sustainable profitability.",

                "strategic_warning":
                    "Revenue without healthy margins creates hidden risk.",

                "executive_summary":
                    "Profitable growth compounds; inefficient growth collapses."
            }

        # ==========================================
        # CUSTOMER ACQUISITION
        # ==========================================

        if objective == "customer_acquisition":

            return {

                "current_priority":
                    "Acquire customers efficiently.",

                "execution_focus":
                    "Optimize channels, conversion rates, and customer acquisition costs.",

                "growth_blocker":
                    "Weak differentiation leading to expensive acquisition.",

                "next_business_evolution":
                    "Build scalable acquisition systems.",

                "strategic_warning":
                    "High acquisition costs can destroy lifetime value.",

                "executive_summary":
                    "The best growth engine balances acquisition and retention."
            }

        # ==========================================
        # LOGISTICS INDUSTRY
        # ==========================================

        if industry == "logistics":

            return {

                "current_priority":
                    "Improve network efficiency.",

                "execution_focus":
                    "Increase fleet utilization, route density, and driver retention.",

                "growth_blocker":
                    "Operational inefficiencies reducing margins.",

                "next_business_evolution":
                    "Develop regional logistics advantages and scale.",

                "strategic_warning":
                    "Logistics margins deteriorate quickly under poor execution.",

                "executive_summary":
                    "Operational excellence is the strongest competitive advantage in logistics."
            }

        # ==========================================
        # HEALTHCARE INDUSTRY
        # ==========================================

        if industry == "healthcare":

            return {

                "current_priority":
                    "Strengthen patient value.",

                "execution_focus":
                    "Increase retention, optimize scheduling, and improve payer mix.",

                "growth_blocker":
                    "Capacity constraints and administrative inefficiencies.",

                "next_business_evolution":
                    "Create recurring patient relationships.",

                "strategic_warning":
                    "Volume growth without quality control damages reputation.",

                "executive_summary":
                    "Trust and efficiency determine long-term healthcare success."
            }

        # ==========================================
        # AI / SAAS
        # ==========================================

        if industry in ["ai", "saas"]:

            return {

                "current_priority":
                    "Strengthen product-market fit.",

                "execution_focus":
                    "Increase retention, improve user outcomes, and reinforce switching costs.",

                "growth_blocker":
                    "Feature parity without differentiation.",

                "next_business_evolution":
                    "Build ecosystem advantages and recurring revenue.",

                "strategic_warning":
                    "Rapid growth without defensibility invites commoditization.",

                "executive_summary":
                    "Winning SaaS companies become difficult to replace."
            }

        # ==========================================
        # FINANCE
        # ==========================================

        if industry == "finance":

            return {

                "current_priority":
                    "Build trust and resilience.",

                "execution_focus":
                    "Compliance, risk controls, and customer confidence.",

                "growth_blocker":
                    "Regulatory exposure.",

                "next_business_evolution":
                    "Scale through credibility and infrastructure.",

                "strategic_warning":
                    "Ignoring risk controls can destroy institutional trust.",

                "executive_summary":
                    "Trust compounds faster than marketing in finance."
            }

        # ==========================================
        # DEFAULT EXECUTIVE REASONING
        # ==========================================

        return {

            "current_priority":
                "Clarify strategic priorities.",

            "execution_focus":
                strategic_direction
                or "Improve execution discipline and customer understanding.",

            "growth_blocker":
                f"Competitive pressure: {competition}.",

            "next_business_evolution":
                f"Strengthen strategic positioning using {moat}.",

            "strategic_warning":
                "Avoid scaling before validating assumptions.",

            "executive_summary":
                "Sustainable growth requires disciplined execution and clear differentiation."
        }


dynamic_reasoning_engine = (
    DynamicReasoningEngine()
)