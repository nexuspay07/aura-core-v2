class CausalReasoningEngine:
    """
    Aura causal reasoning layer.
    Applies simple cause-effect logic to the current world state
    before strategy prediction and ranking.
    """

    def __init__(self):
        self.knowledge_graph = {}
        print("[CAUSAL REASONING ENGINE] Initialized")

    def analyze_causality(self, world_state: dict, context: dict | None = None, memories: list | None = None):
        updated_state = world_state.copy()
        context = context or {}
        memories = memories or []

        # ---------------------------------
        # Business-style causal rules
        # ---------------------------------

        # Higher competition reduces growth confidence
        if "competition" in updated_state and "market_growth" in updated_state:
            updated_state["market_growth"] = max(
                updated_state["market_growth"] - (updated_state["competition"] * 0.15),
                0
            )

        # Higher risk level increases instability
        if "risk_level" in updated_state and "market_growth" in updated_state:
            updated_state["market_growth"] = max(
                updated_state["market_growth"] - (updated_state["risk_level"] * 0.1),
                0
            )

        # Budget influences opportunity strength
        if "budget" in updated_state and "market_growth" in updated_state:
            if updated_state["budget"] > 20000:
                updated_state["market_growth"] += 0.1
            elif updated_state["budget"] < 5000:
                updated_state["market_growth"] = max(
                    updated_state["market_growth"] - 0.1,
                    0
                )

        # Optional context influence
        if context.get("market_trend") == "down":
            updated_state["market_growth"] = max(
                updated_state.get("market_growth", 0.5) * 0.9,
                0
            )

        if context.get("market_trend") == "up":
            updated_state["market_growth"] = min(
                updated_state.get("market_growth", 0.5) * 1.1,
                1.5
            )

        return updated_state


causal_reasoning_engine = CausalReasoningEngine()