# app/lab/agent_engine.py

import random

class AgentEngine:

    def __init__(self):
        self.agents = [
            {"name": "Planner", "type": "planner"},
            {"name": "Executor", "type": "executor"},
            {"name": "Analyst", "type": "analyst"},
            {"name": "RiskAgent", "type": "risk"},
            {"name": "FinanceAgent", "type": "finance"},
            {"name": "MarketAgent", "type": "market"},
            {"name": "EthicsAgent", "type": "ethics"},
        ]

    # ==========================================
    # MAIN ENTRY
    # ==========================================
    def run_agents(self, sim_result):
        steps = []
        strategies = sim_result.get("results", [])

        # -----------------------------
        # BASE SYSTEM AGENTS
        # -----------------------------
        steps.append({
            "agent": "Planner",
            "message": "Generating strategies based on goal",
            "status": "done"
        })

        steps.append({
            "agent": "Executor",
            "message": "Running simulations on all strategies",
            "status": "done"
        })

        # -----------------------------
        # 🔥 PHASE 16 — INTELLIGENCE AGENTS
        # -----------------------------
        for strategy in strategies:

            strategy.setdefault("agent_scores", 0)

            # ===== RISK AGENT =====
            risk_score = random.uniform(-2, 1)
            strategy["agent_scores"] += risk_score

            steps.append({
                "agent": "RiskAgent",
                "message": f"{strategy['name']} risk impact: {round(risk_score,2)}",
                "status": "evaluated"
            })

            # ===== FINANCE AGENT =====
            budget = sim_result.get("budget", 10000)
            finance_score = 1 if budget > 5000 else -2
            strategy["agent_scores"] += finance_score

            steps.append({
                "agent": "FinanceAgent",
                "message": f"{strategy['name']} budget score: {finance_score}",
                "status": "evaluated"
            })

            # ===== MARKET AGENT =====
            market = sim_result.get("market", "normal")

            if market == "high":
                market_score = 2
            elif market == "low":
                market_score = -1
            else:
                market_score = 1

            strategy["agent_scores"] += market_score

            steps.append({
                "agent": "MarketAgent",
                "message": f"{strategy['name']} market score: {market_score}",
                "status": "evaluated"
            })

            # ===== ETHICS AGENT =====
            ethics_score = random.choice([0, 1])  # simple compliance
            strategy["agent_scores"] += ethics_score

            ethics_score = random.choice([0, 1])

            if ethics_score == 0:
                strategy["ethics_flag"] = "ok"
            else:
                strategy["ethics_flag"] = "ok"

            steps.append({
                "agent": "EthicsAgent",
                "message": f"{strategy['name']} ethics score: {ethics_score}",
                "status": "evaluated"
            })

            # ===== FINAL SCORE UPDATE =====
            base_score = strategy.get("score", 0)
            strategy["final_score"] = base_score + strategy["agent_scores"]

        # -----------------------------
        # ANALYST (FINAL DECISION)
        # -----------------------------
        best = max(strategies, key=lambda x: x.get("final_score", 0))


        steps.append({
            "agent": "Analyst",
            "message": "Comparing all strategies with multi-agent scores",
            "status": "done"
        })

        steps.append({
            "agent": "System",
            "message": f"Best strategy selected: {best['name']} (score: {round(best['final_score'],2)})",
            "status": "final"
        })

        return steps


# ✅ GLOBAL INSTANCE
agent_engine = AgentEngine()