class SelfLearningEngine:

    def __init__(self):
        self.history = []

    # ==========================================
    # RECORD EXPERIENCE
    # ==========================================
    def record(self, goal, plan, results):
        success_score = self.evaluate(results)

        entry = {
            "goal": goal,
            "plan": plan,
            "results": results,
            "success_score": success_score
        }

        self.history.append(entry)

        return entry

    # ==========================================
    # EVALUATE PERFORMANCE
    # ==========================================
    def evaluate(self, results):
        if not results:
            return 0

        success_count = sum(1 for r in results if r.get("status") == "completed")

        return success_count / len(results)

    # ==========================================
    # GET BEST STRATEGY
    # ==========================================
    def get_best_strategy(self, goal):
        relevant = [h for h in self.history if h["goal"] == goal]

        if not relevant:
            return None

        best = max(relevant, key=lambda x: x["success_score"])
        return best["plan"]

    # ==========================================
    # GET INSIGHTS
    # ==========================================
    def get_insights(self):
        if not self.history:
            return {"message": "No learning data yet"}

        avg_score = sum(h["success_score"] for h in self.history) / len(self.history)

        return {
            "total_runs": len(self.history),
            "average_success": avg_score
        }


# ✅ GLOBAL INSTANCE
self_learning_engine = SelfLearningEngine()