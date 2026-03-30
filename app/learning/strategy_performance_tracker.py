# app/learning/strategy_performance_tracker.py

class StrategyPerformanceTracker:
    def __init__(self):
        # Stores performance records for each strategy
        # Each record is a dict: {"strategy_id": ..., "score": ..., "success": ...}
        self.records = []

    def record_performance(self, strategy_id, score, success):
        """Record a new performance for a strategy."""
        record = {
            "strategy_id": strategy_id,
            "score": score,
            "success": success
        }
        self.records.append(record)

    def get_recent_metrics(self, n=10):
        """
        Returns the most recent n performance records.
        Default is 10. Returns a list of dicts.
        """
        return self.records[-n:]

    def get_all_statistics(self):
        """
        Return aggregated statistics for all strategies.
        Example: average score per strategy.
        """
        stats = {}
        for rec in self.records:
            sid = rec["strategy_id"]
            if sid not in stats:
                stats[sid] = {"total_score": 0, "count": 0, "success_count": 0}
            stats[sid]["total_score"] += rec["score"]
            stats[sid]["count"] += 1
            if rec["success"]:
                stats[sid]["success_count"] += 1

        # Compute averages
        for sid, data in stats.items():
            data["avg_score"] = data["total_score"] / data["count"]
            data["success_rate"] = data["success_count"] / data["count"]

            {
    "strategy_id": "strategy_1",
    "score": 0.85,
    "success": True
}

        return stats

# Singleton instance for import
strategy_performance_tracker = StrategyPerformanceTracker()