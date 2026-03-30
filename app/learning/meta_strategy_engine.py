class MetaStrategyEngine:

    def __init__(self, strategy_performance_tracker):
        self.strategy_performance_tracker = strategy_performance_tracker
        print("[META STRATEGY ENGINE] Initialized")

    def analyze_strategy_patterns(self):

        stats = self.strategy_performance_tracker.get_all_statistics()

        insights = []

        for strategy_id, data in stats.items():

            # Case 1: data is already a statistics dictionary
            if isinstance(data, dict):

                runs = data.get("runs", 0)
                successes = data.get("successes", 0)
                avg_score = data.get("average_score", 0)

            # Case 2: data is a list of results
            elif isinstance(data, list):

                runs = len(data)
                successes = sum(1 for r in data if r.get("success", False))
                total_score = sum(r.get("score", 0) for r in data)

                avg_score = 0
                if runs > 0:
                    avg_score = total_score / runs

            else:
                continue

            success_rate = 0
            if runs > 0:
                success_rate = successes / runs

            insight = {
                "strategy_id": strategy_id,
                "runs": runs,
                "success_rate": success_rate,
                "average_score": avg_score
            }

            insights.append(insight)

        print("[META STRATEGY] Pattern analysis completed")

        return insights


meta_strategy_engine = None
