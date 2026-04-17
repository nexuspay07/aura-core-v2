# app/lab/failure_engine.py

class FailureEngine:

    def predict(self, strategies, scenario, world):
        failures = []

        for s in strategies:
            name = s.get("name")
            risk = s.get("risk", "medium")
            score = s.get("final_score", s.get("score", 0))

            failure_risk = 0.0
            reasons = []

            # =============================
            # ⚠️ RISK BASE
            # =============================
            if risk == "high":
                failure_risk += 0.4
                reasons.append("High-risk strategy")
            elif risk == "medium":
                failure_risk += 0.25
            else:
                failure_risk += 0.1

            # =============================
            # 💰 LOW BUDGET RISK
            # =============================
            if scenario.get("budget", 0) < 3000:
                failure_risk += 0.2
                reasons.append("Low budget constraint")

            # =============================
            # 📉 MARKET CONDITIONS
            # =============================
            if world.get("competition", 0) > 0.7:
                failure_risk += 0.2
                reasons.append("High competition")

            # =============================
            # 📊 LOW SCORE PENALTY
            # =============================
            if score < 2:
                failure_risk += 0.2
                reasons.append("Weak performance score")

            # Clamp
            failure_risk = min(1.0, failure_risk)

            failures.append({
                "strategy": name,
                "failure_probability": round(failure_risk * 100, 2),
                "risk": risk,
                "reasons": reasons
            })

        return failures


# ✅ instance
failure_engine = FailureEngine()