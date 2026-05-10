class OperationalIntelligenceEngine:
    """
    Operational Intelligence Layer

    This engine helps AURA understand how a business runs internally:
    execution pressure, founder dependency, scalability, workflow load,
    operational bottlenecks, and systemization level.
    """

    def analyze(
        self,
        goal: str,
        business_dna: dict,
        dynamic_reasoning: dict,
        strategic_simulation: dict | None = None
    ):
        strategic_simulation = strategic_simulation or {}

        model = business_dna.get("business_model", "general_business")
        stage = business_dna.get("business_stage", "unknown_stage")
        capital = business_dna.get("capital_intensity", "medium")
        complexity = business_dna.get("operational_complexity", "medium")
        scalability = business_dna.get("scalability", "medium")
        trust = business_dna.get("trust_dependency", "medium")
        channel = business_dna.get("primary_channel", "unknown_channel")

        execution_warning = dynamic_reasoning.get(
            "strategic_warning",
            "Execution risk depends on validation and operational discipline."
        )

        return {
            "operational_stability": self._operational_stability(stage, complexity, capital),
            "execution_load": self._execution_load(stage, complexity, trust),
            "founder_dependency": self._founder_dependency(stage, model),
            "team_pressure": self._team_pressure(stage, complexity),
            "scalability_risk": self._scalability_risk(scalability, complexity),
            "systemization_score": self._systemization_score(stage, model, channel),
            "main_operational_bottleneck": self._main_bottleneck(model, stage, complexity),
            "workflow_risk": self._workflow_risk(model, complexity),
            "operational_warning": execution_warning,
            "recommended_operational_move": self._recommended_move(stage, model),
            "operations_next_steps": self._next_steps(stage, model),
            "scale_readiness": self._scale_readiness(stage, scalability, complexity),
        }

    def _operational_stability(self, stage, complexity, capital):
        if stage == "early_stage":
            return "Low to medium — the business is still proving its operating model."

        if stage == "growth_stage":
            if complexity in ["high", "very_high"]:
                return "Medium — growth is increasing pressure on operations."
            return "Medium to high — operations can improve if systems are strengthened."

        if stage == "survival_stage":
            return "Low — the business needs stabilization before scaling."

        if capital in ["high", "very_high"]:
            return "Medium — spending pressure can affect stability."

        return "Medium — stability depends on execution consistency."

    def _execution_load(self, stage, complexity, trust):
        if complexity in ["high", "very_high"]:
            return "High — delivery, trust-building, and execution quality require strong attention."

        if stage == "early_stage" and trust in ["high", "very_high"]:
            return "Medium-high — proof-building and customer trust will require active effort."

        if stage == "growth_stage":
            return "High — scaling increases execution load."

        return "Medium — execution must stay focused and measurable."

    def _founder_dependency(self, stage, model):
        if stage == "early_stage":
            return "High — most execution still depends on the founder."

        if model in ["service_business", "digital_product_or_platform"]:
            return "Medium-high — delivery quality may still depend heavily on key people."

        if stage == "growth_stage":
            return "Medium — systems should start replacing founder-only execution."

        return "Medium"

    def _team_pressure(self, stage, complexity):
        if stage == "early_stage":
            return "Low now, but pressure rises quickly if demand increases."

        if stage == "growth_stage" and complexity in ["high", "very_high"]:
            return "High — team or process capacity may become a bottleneck."

        if stage == "survival_stage":
            return "High — financial and operational pressure may strain the team."

        return "Medium"

    def _scalability_risk(self, scalability, complexity):
        if scalability in ["low", "medium"] and complexity in ["high", "very_high"]:
            return "High — scaling may break operations unless processes are simplified."

        if scalability in ["high", "very_high"] and complexity in ["high", "very_high"]:
            return "Medium-high — the opportunity can scale, but operations must be systemized."

        if scalability in ["high", "very_high"]:
            return "Medium — scalable potential exists, but execution systems must mature."

        return "Medium"

    def _systemization_score(self, stage, model, channel):
        if stage == "early_stage":
            return "Low — the business likely does not yet have repeatable systems."

        if model == "digital_product_or_platform":
            return "Medium — systems can be built through onboarding, automation, and analytics."

        if model == "service_business":
            return "Medium-low — services need repeatable delivery playbooks."

        if channel == "offline":
            return "Medium — offline operations require consistent workflows and staff discipline."

        return "Medium"

    def _main_bottleneck(self, model, stage, complexity):
        if stage == "early_stage":
            if model == "digital_product_or_platform":
                return "Proof of value and repeatable customer onboarding."
            if model == "service_business":
                return "Consistent client acquisition and delivery quality."
            return "Turning the idea into repeatable customer demand."

        if stage == "growth_stage":
            if complexity in ["high", "very_high"]:
                return "Operational capacity and process consistency."
            return "Scaling acquisition without reducing quality."

        if stage == "survival_stage":
            return "Cash control, simplified operations, and profitability."

        return "Execution clarity and repeatable workflows."

    def _workflow_risk(self, model, complexity):
        if complexity in ["high", "very_high"]:
            return "High — unclear workflows can slow delivery and reduce customer trust."

        if model == "digital_product_or_platform":
            return "Medium — onboarding and customer activation must be smooth."

        if model == "service_business":
            return "Medium-high — inconsistent service delivery can hurt trust."

        return "Medium"

    def _recommended_move(self, stage, model):
        if stage == "early_stage":
            if model == "digital_product_or_platform":
                return "Build one repeatable onboarding and proof system before scaling acquisition."
            if model == "service_business":
                return "Create a repeatable service delivery checklist before taking more clients."
            return "Document the first repeatable customer journey before scaling."

        if stage == "growth_stage":
            return "Standardize operations before increasing customer acquisition."

        if stage == "survival_stage":
            return "Simplify the offer, cut operational waste, and stabilize cash flow."

        return "Clarify the workflow, document the process, and measure execution quality."

    def _next_steps(self, stage, model):
        if stage == "early_stage":
            return [
                "Write down the exact customer journey from first contact to successful result",
                "Identify the step where customers are most likely to drop off",
                "Create one repeatable process before adding more complexity"
            ]

        if stage == "growth_stage":
            return [
                "Document the core operating process",
                "Assign ownership for repeated tasks",
                "Create basic metrics for delivery speed, quality, and customer satisfaction"
            ]

        if stage == "survival_stage":
            return [
                "List the most expensive or time-consuming operational activities",
                "Remove or simplify anything not tied to revenue or customer value",
                "Stabilize the highest-risk bottleneck first"
            ]

        return [
            "Map the business workflow",
            "Identify bottlenecks",
            "Create repeatable systems"
        ]

    def _scale_readiness(self, stage, scalability, complexity):
        if stage == "early_stage":
            return "Not ready to scale yet — validate demand and systemize delivery first."

        if stage == "growth_stage":
            if scalability in ["high", "very_high"] and complexity not in ["high", "very_high"]:
                return "Partially ready — scaling is possible if systems and metrics are strengthened."
            return "Not fully ready — operations may struggle under higher volume."

        if stage == "survival_stage":
            return "Not ready — stabilize before scaling."

        return "Unclear — more operational data is needed."


operational_intelligence_engine = OperationalIntelligenceEngine()