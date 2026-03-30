class StrategyMetaLearningEngine:

    def __init__(self):

        self.context_memory = {}

        print("[STRATEGY META LEARNING ENGINE] Initialized")

    def extract_context(self, kpis):

        context = []

        if kpis["wait_time"] > 15:
            context.append("high_wait")

        if kpis["capacity"] < 120:
            context.append("low_capacity")

        if kpis["staff"] < 10:
            context.append("low_staff")

        if not context:
            context.append("normal")

        return "_".join(context)

    def learn(self, context, strategy, reward):

        if context not in self.context_memory:
            self.context_memory[context] = {}

        if strategy not in self.context_memory[context]:
            self.context_memory[context][strategy] = 0

        self.context_memory[context][strategy] += reward

    def get_best_strategy(self, context):

        if context not in self.context_memory:
            return None

        strategies = self.context_memory[context]

        return max(strategies, key=strategies.get)

    def get_memory(self):

        return self.context_memory


# Global instance
strategy_meta_learning_engine = StrategyMetaLearningEngine()