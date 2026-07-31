from typing import Dict, List


class MemorySelector:
    """
    Filters memories after retrieval.

    If semantic search is unavailable,
    falls back to lightweight keyword matching.
    """

    def select_relevant(
        self,
        memories: List[Dict],
        query: str,
        max_memories: int = 3,
    ) -> List[Dict]:

        query_words = set(query.lower().split())

        scored = []

        for memory in memories:

            content = (
                memory.get("content")
                or ""
            )

            memory_words = set(
                content.lower().split()
            )

            overlap = len(
                query_words.intersection(
                    memory_words
                )
            )

            scored.append(
                (
                    overlap,
                    memory,
                )
            )

        scored.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        return [
            item[1]
            for item in scored[:max_memories]
            if item[0] > 0
        ]


memory_selector = MemorySelector()