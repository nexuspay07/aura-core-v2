class ExplanationEngine:

    def explain_step(self, step, goal, context=None):
        try:
            description = step.get("description", "Unknown step")
            goal_name = goal.get("name", "goal")

            explanation = f"This step is included to help achieve '{goal_name}'. "

            # Simple reasoning (can upgrade later)
            if "analyze" in description.lower():
                explanation += "It gathers insights before decision-making."
            elif "design" in description.lower():
                explanation += "It structures an effective solution."
            elif "execute" in description.lower():
                explanation += "It implements the planned solution."
            else:
                explanation += "It contributes to overall goal completion."

            return explanation

        except Exception as e:
            return f"Explanation error: {str(e)}"


# ✅ GLOBAL INSTANCE
explanation_engine = ExplanationEngine()