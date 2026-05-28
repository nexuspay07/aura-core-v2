# app/core/memory/memory_priority_retrieval_engine.py


class MemoryPriorityRetrievalEngine:

    def __init__(self):

        print(
            "[MEMORY PRIORITY RETRIEVAL ENGINE] Initialized"
        )

    def retrieve_priority_memories(
        self,
        memory_objects,
        minimum_score=15
    ):

        ranked_memories = []

        for memory in memory_objects:

            importance = memory.get(
                "importance_score",
                10
            )

            semantic_score = memory.get(
                "semantic_score",
                0.5
            )

            reinforcement_strength = memory.get(
                "reinforcement_strength",
                1.0
            )

            decay_factor = memory.get(
                "decay_factor",
                1.0
            )

            confidence = memory.get(
                "confidence",
                0.5
            )

            recall_count = memory.get(
                "recall_count",
                1
            )

            final_score = (
                (importance * 0.35)
                + (semantic_score * 25)
                + (reinforcement_strength * 0.20)
                + (confidence * 15)
                + (recall_count * 0.05)
            ) * decay_factor

            memory["final_cognitive_score"] = round(
                final_score,
                2
            )

            if final_score >= minimum_score:

                ranked_memories.append(memory)

        ranked_memories.sort(
            key=lambda x: x["final_cognitive_score"],
            reverse=True
        )

        return ranked_memories


memory_priority_retrieval_engine = (
    MemoryPriorityRetrievalEngine()
)