# app/core/self_evaluation_engine.py

class SelfEvaluationEngine:
    def __init__(self):
        print("[SELF-EVALUATION ENGINE] Adaptive Evaluation Enabled")

    def evaluate(self, goal, plan, execution_results, context):
        """
        Evaluate the execution of a plan for a given goal.
        Returns a dict with:
            - score (float 0.0-1.0)
            - status (str: 'good', 'average', 'poor')
        """
        if not plan:
            score = 0.0
        else:
            # Simple scoring: percentage of actions executed successfully
            completed = sum(1 for r in execution_results if r.get("status") == "completed")
            score = completed / len(plan)

        # Determine status
        if score >= 0.75:
            status = "good"
        elif score >= 0.4:
            status = "average"
        else:
            status = "poor"

        print(f"[SELF-EVALUATION] Goal: {goal['name']} | Score: {score:.2f} | Status: {status}")

        return {"score": score, "status": status}

# Instantiate global engine
self_evaluation_engine = SelfEvaluationEngine()