import json
import os
from datetime import datetime
from typing import List, Dict, Any


class IntelligenceMemory:

    def __init__(self):

        self.memory_file = "intelligence_memory.json"
        self.memories: List[Dict[str, Any]] = []

        self._load_memory()

    def _load_memory(self):

        if os.path.exists(self.memory_file):

            try:
                with open(self.memory_file, "r") as f:
                    self.memories = json.load(f)

            except Exception:
                self.memories = []

        else:
            self.memories = []

    def _save_memory(self):

        with open(self.memory_file, "w") as f:
            json.dump(self.memories, f, indent=4)

    def store(self, memory: Dict[str, Any]):

        memory_record = {
            "id": len(self.memories) + 1,
            "timestamp": datetime.utcnow().isoformat(),
            "data": memory
        }

        self.memories.append(memory_record)

        self._save_memory()

        return memory_record

    def recall(self, limit: int = 10):

        return self.memories[-limit:]

    def total_memories(self):

        return len(self.memories)


# global instance
intelligence_memory = IntelligenceMemory()