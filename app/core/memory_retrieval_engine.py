# app/core/memory_retrieval_engine.py

class MemoryRetrievalEngine:
    def __init__(self):
        """
        Initialize the Memory Retrieval Engine.
        """
        print("[MEMORY RETRIEVAL ENGINE] Initialized")
        # Store all memories here
        self.memory_store = []

    def retrieve(self, context):
        """
        Retrieve relevant memories based on the current context.

        Args:
            context (dict): Current context data from ContextEngine.

        Returns:
            list: Relevant memories.
        """
        relevant = []

        # Simple matching: check if all context key-value pairs are in memory
        for memory in self.memory_store:
            if isinstance(memory, dict):
                match = all(item in memory.items() for item in context.items())
                if match:
                    relevant.append(memory)

        # Debug output
        print(f"[MEMORY RETRIEVAL ENGINE] Retrieved {len(relevant)} relevant memories for context")
        return relevant

    def store(self, memory):
        """
        Store a memory in the engine.

        Args:
            memory (dict): Memory to store.
        """
        if isinstance(memory, dict):
            self.memory_store.append(memory)
            print(f"[MEMORY RETRIEVAL ENGINE] Stored memory: {memory}")
        else:
            print("[MEMORY RETRIEVAL ENGINE] Warning: Memory must be a dictionary")

# Global instance for import elsewhere
memory_retrieval_engine = MemoryRetrievalEngine()