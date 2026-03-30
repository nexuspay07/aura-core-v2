# app/lab/arbitration_engine.py

class ArbitrationEngine:

    def __init__(self):
        # 🔥 Agent authority weights
        self.weights = {
            "risk": 2.0,
            "finance": 1.5,
            "market": 1.2,
            "ethics": 3.0
        }

    # ==========================================
    # MAIN ARBITRATION FUNCTION
    # ==========================================
    def arbitrate(self, strategies, scenario):
        for strategy in strategies:

            base_score = strategy.get("score", 0)
            agent_score = strategy.get("agent_scores", 0)

            # 🔥 Weighted adjustment
            weighted_score = (
                agent_score * 1.5  # amplify agent intelligence
            )

            final_score = base_score + weighted_score

            # ==================================
            # 🔥 HARD RULES (VETO SYSTEM)
            # ==================================

            # ❌ ETHICS VETO
            if strategy.get("ethics_flag") == "violation":
                final_score = -999
                strategy["rejected"] = True
                strategy["rejection_reason"] = "Ethics violation"

            # ❌ HIGH RISK BLOCK (based on tolerance)
            risk_tolerance = scenario.get("risk_tolerance", 0.5)

            if strategy.get("risk") == "high" and risk_tolerance < 0.4:
                final_score -= 3  # heavy penalty

            # ❌ LOW BUDGET PENALTY
            budget = scenario.get("budget", 0)
            if budget < 5000:
                final_score -= 2

            # ==================================
            # SAVE FINAL SCORE
            # ==================================
            strategy["final_score"] = final_score

        # ==================================
        # SELECT BEST VALID STRATEGY
        # ==================================
        valid_strategies = [s for s in strategies if not s.get("rejected")]

        if not valid_strategies:
            return None, "All strategies rejected by arbitration engine"

        best = max(valid_strategies, key=lambda x: x["final_score"])

        return best, "Arbitration complete"


# ✅ GLOBAL INSTANCE
arbitration_engine = ArbitrationEngine()