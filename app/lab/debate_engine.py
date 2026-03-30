# app/lab/debate_engine.py

import random


class DebateEngine:

    def run_debate(self, strategies, goal):
        debates = []

        for i in range(len(strategies)):
            for j in range(len(strategies)):
                if i == j:
                    continue

                attacker = strategies[i]
                defender = strategies[j]

                critique, defense = self.generate_arguments(
                    attacker["name"],
                    defender["name"],
                    goal
                )

                # 🎯 Impact (who wins the argument)
                impact = random.uniform(-0.3, 0.3)

                # Apply impact to defender score
                defender["score"] += impact

                debates.append({
                    "attacker": attacker["name"],
                    "defender": defender["name"],
                    "critique": critique,
                    "defense": defense,
                    "impact": impact
                })

        return strategies, debates

    # ==========================================
    # 🧠 STRATEGY-AWARE ARGUMENTS
    # ==========================================
    def generate_arguments(self, attacker, defender, goal):

        # AGGRESSIVE attacking others
        if attacker == "Aggressive":
            if defender == "Balanced":
                critique = f"{defender} is too cautious and may miss rapid growth opportunities for '{goal}'."
                defense = f"{defender} argues that controlled scaling ensures long-term sustainability."
            elif defender == "Conservative":
                critique = f"{defender} is too slow and risks stagnation in achieving '{goal}'."
                defense = f"{defender} argues that minimizing losses is more important than rapid expansion."
            else:
                critique = f"{defender} lacks the speed required for '{goal}'."
                defense = f"{defender} defends its approach as stable and reliable."

        # BALANCED attacking others
        elif attacker == "Balanced":
            if defender == "Aggressive":
                critique = f"{defender} carries excessive risk and may lead to instability in '{goal}'."
                defense = f"{defender} argues that high risk brings high reward."
            elif defender == "Conservative":
                critique = f"{defender} is overly cautious and may delay achieving '{goal}'."
                defense = f"{defender} argues that slow growth avoids major failures."
            else:
                critique = f"{defender} lacks balance in execution."
                defense = f"{defender} maintains its strategy is sufficient."

        # CONSERVATIVE attacking others
        elif attacker == "Conservative":
            if defender == "Aggressive":
                critique = f"{defender} is too risky and could result in major losses for '{goal}'."
                defense = f"{defender} argues that bold moves are necessary for success."
            elif defender == "Balanced":
                critique = f"{defender} still carries unnecessary risk for '{goal}'."
                defense = f"{defender} argues it balances safety and growth effectively."
            else:
                critique = f"{defender} is unpredictable."
                defense = f"{defender} defends its flexibility."

        else:
            critique = f"{attacker} questions {defender}'s effectiveness."
            defense = f"{defender} defends its approach."

        return critique, defense


# ✅ instance
debate_engine = DebateEngine()