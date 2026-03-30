class StrategyFitnessEngine:

    def __init__(self):

        print("[STRATEGY FITNESS ENGINE] Initialized")

    def calculate_fitness(self, kpis):

        patients = kpis["patients"]
        staff = kpis["staff"]
        capacity = kpis["capacity"]
        wait_time = kpis["wait_time"]

        # Throughput score
        throughput_score = patients / capacity if capacity > 0 else 0

        # Efficiency score
        efficiency_score = patients / staff if staff > 0 else 0

        # Wait penalty
        wait_penalty = max(0, 1 - (wait_time / 100))

        fitness = (
            throughput_score * 0.4 +
            efficiency_score * 0.4 +
            wait_penalty * 0.2
        )

        return {
            "throughput_score": throughput_score,
            "efficiency_score": efficiency_score,
            "wait_penalty": wait_penalty,
            "fitness": fitness
        }


# Global instance
strategy_fitness_engine = StrategyFitnessEngine()