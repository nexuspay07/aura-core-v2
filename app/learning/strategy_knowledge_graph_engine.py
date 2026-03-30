class StrategyKnowledgeGraphEngine:

    def __init__(self):

        # Graph structure: parent_strategy -> [child_strategies]
        self.strategy_graph = {}

        print("[STRATEGY KNOWLEDGE GRAPH ENGINE] Initialized")

    def add_relationship(self, parent, child):

        if parent not in self.strategy_graph:
            self.strategy_graph[parent] = []

        if child not in self.strategy_graph[parent]:
            self.strategy_graph[parent].append(child)

        return {
            "parent": parent,
            "child": child
        }

    def get_children(self, strategy):

        return self.strategy_graph.get(strategy, [])

    def get_graph(self):

        return self.strategy_graph


# Global instance
strategy_knowledge_graph_engine = StrategyKnowledgeGraphEngine()