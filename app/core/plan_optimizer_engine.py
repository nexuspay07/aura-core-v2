class PlanOptimizerEngine:

    def optimize(self, plan, goal, context):
        optimized_plan = []

        for step in plan:
            description = step.get("description", "")

            # 🔍 Rule 1: Improve vague steps
            if "analyze" in description.lower():
                step["description"] = f"Deep analysis of {goal.get('name')} using available data"

            # 🔍 Rule 2: Strengthen execution clarity
            if "execute" in description.lower():
                step["description"] = f"Execute optimized solution for {goal.get('name')}"

            # 🔍 Rule 3: Remove weak steps
            if len(description.strip()) < 5:
                continue

            # 🔍 Rule 4: Add intelligence tag
            step["optimized"] = True

            optimized_plan.append(step)

        # 🔁 Reorder (simple priority logic)
        optimized_plan = sorted(optimized_plan, key=lambda x: x.get("step_id", 0))

        return optimized_plan


# ✅ GLOBAL INSTANCE
plan_optimizer_engine = PlanOptimizerEngine()