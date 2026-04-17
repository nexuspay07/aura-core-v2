class ExplanationEngine:
    def generate(self, best, results, failures=None, world=None):
        explanations = []

        # =============================
        # SAFETY CHECKS
        # =============================
        if not isinstance(results, list) or len(results) == 0:
            return ["AURA could not generate a valid set of strategies."]

        if not isinstance(best, dict) or not best:
            return ["AURA could not determine a best strategy."]

        # =============================
        # BASIC VALUES
        # =============================
        name = best.get("name", "Unknown")
        final_score = best.get("final_score", best.get("score", 0))
        decision_score = best.get("decision_score", final_score)
        trust_score = best.get("trust_score", 0)
        risk = best.get("risk", "unknown")
        confidence_score = best.get("confidence_score", best.get("confidence", 0))

        # =============================
        # SORT RESULTS
        # =============================
        sorted_results = sorted(
            results,
            key=lambda x: x.get("decision_score", x.get("final_score", x.get("score", 0))),
            reverse=True
        )

        runner_up = sorted_results[1] if len(sorted_results) > 1 else None

        # =============================
        # FAILURE INFO
        # =============================
        best_failure = None
        if isinstance(failures, list):
            best_failure = next(
                (f for f in failures if f.get("strategy") == name),
                None
            )

        failure_probability = 0
        failure_reasons = []
        if best_failure:
            failure_probability = best_failure.get("failure_probability", 0)
            failure_reasons = best_failure.get("reasons", [])

        # =============================
        # 1. EXECUTIVE SUMMARY
        # =============================
        explanations.append(
            f"AURA recommends '{name}' as the best strategy because it produced the strongest risk-adjusted outcome, not just the highest raw score."
        )

        # =============================
        # 2. WHY IT WON
        # =============================
        explanations.append(
            f"It finished with a final score of {final_score:.2f}, a decision score of {decision_score:.2f}, and a trust score of {trust_score:.2f}."
        )

        # Risk explanation
        if risk == "high":
            explanations.append(
                "It is an aggressive strategy with higher upside, but also higher exposure to failure."
            )
        elif risk == "medium":
            explanations.append(
                "It balances growth and caution, which makes it more resilient in uncertain conditions."
            )
        elif risk == "low":
            explanations.append(
                "It prioritizes stability and downside protection, which makes it stronger when reliability matters more than speed."
            )
        else:
            explanations.append(
                "Its risk profile is unclear, but it still performed strongly overall."
            )

        # =============================
        # 3. HUMAN-LEVEL COMPARISON 🔥
        # =============================
        if runner_up:
            runner_name = runner_up.get("name", "Unknown")
            runner_decision = runner_up.get(
                "decision_score",
                runner_up.get("final_score", runner_up.get("score", 0))
            )

            diff = decision_score - runner_decision

            if diff < 0.5:
                explanations.append(
                    f"The decision was very close, but '{name}' slightly edged out '{runner_name}' due to better risk-adjusted performance."
                )
            elif diff < 1.5:
                explanations.append(
                    f"'{name}' performed moderately better than '{runner_name}', mainly due to stronger reliability under current conditions."
                )
            else:
                explanations.append(
                    f"'{name}' clearly outperformed '{runner_name}', showing a significant advantage in this scenario."
                )

        # =============================
        # 4. FAILURE ANALYSIS
        # =============================
        if failure_probability > 0:
            if failure_reasons:
                explanations.append(
                    f"Its estimated failure probability is {failure_probability:.1f}%, driven mainly by {', '.join(failure_reasons)}."
                )
            else:
                explanations.append(
                    f"Its estimated failure probability is {failure_probability:.1f}%, meaning it is promising but not risk-free."
                )
        else:
            explanations.append(
                "No major failure signal was detected for this strategy."
            )

        # =============================
        # 5. WORLD CONTEXT
        # =============================
        if isinstance(world, dict):
            market = world.get("market", "unknown")
            competition = world.get("competition", None)

            explanations.append(
                f"This decision was made in a '{market}' market with competition level {round(competition, 2) if competition else 'unknown'}."
            )

        # =============================
        # 6. LOSING STRATEGIES
        # =============================
        for candidate in sorted_results[1:3]:
            explanations.append(
                f"'{candidate.get('name')}' was not selected because it had a weaker decision score and lower overall reliability."
            )

        # =============================
        # 7. ACTION
        # =============================
        if name == "Aggressive":
            explanations.append(
                "Recommended action: move fast, prioritize growth, but monitor risks closely."
            )
        elif name == "Balanced":
            explanations.append(
                "Recommended action: scale gradually, validate demand, and manage risk."
            )
        elif name == "Conservative":
            explanations.append(
                "Recommended action: focus on stability, protect capital, and grow steadily."
            )

        # =============================
        # 8. FINAL HUMAN INSIGHT
        # =============================
        explanations.append(
            f"In plain terms: AURA is not saying '{name}' is perfect. It is saying it is the most defensible decision under current conditions."
        )

        return explanations


# ✅ INSTANCE
explanation_engine = ExplanationEngine()