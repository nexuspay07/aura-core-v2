# app/core/memory/memory_clustering_engine.py

from collections import defaultdict


class MemoryClusteringEngine:

    def __init__(self):
        print("[MEMORY CLUSTERING ENGINE] Initialized")

    def cluster_memories(self, memories):

        clusters = defaultdict(list)

        for memory in memories:

            text = memory.lower()

            if "market" in text:
                clusters["market_intelligence"].append(memory)

            elif "finance" in text:
                clusters["financial"].append(memory)

            elif "strategy" in text:
                clusters["strategy"].append(memory)

            elif "risk" in text:
                clusters["risk"].append(memory)

            elif "customer" in text:
                clusters["customer_behavior"].append(memory)

            else:
                clusters["general"].append(memory)

        return dict(clusters)


memory_clustering_engine = MemoryClusteringEngine()