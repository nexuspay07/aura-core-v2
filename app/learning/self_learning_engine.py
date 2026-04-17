# app/learning/self_learning_engine.py

class SelfLearningEngine:
    def __init__(self):
        self.memory = []

    # ==========================
    # 🔥 NEW METHOD (FIX ERROR)
    # ==========================
    def learn_from_execution(self, goal, sim_result):
        try:
            best = sim_result.get("best_strategy", {})

            learning_entry = {
                "goal": goal,
                "strategy": best.get("name"),
                "score": best.get("final_score"),
                "confidence": best.get("confidence"),
                "timestamp": __import__("datetime").datetime.utcnow().isoformat()
            }

            self.memory.append(learning_entry)

            print(f"[LEARNING] Stored experience: {learning_entry}")

        except Exception as e:
            print(f"[LEARNING ERROR] {str(e)}")

    # ==========================
    # OPTIONAL: GET MEMORY
    # ==========================
    def get_memory(self):
        return self.memory


# ✅ INSTANCE
self_learning_engine = SelfLearningEngine()