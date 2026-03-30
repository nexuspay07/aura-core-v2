from datetime import datetime


class MemoryManager:

    def __init__(self):
        self.memory_store = []
        self.total_memories = 0


    def store(self, organization_id: str, content: str, memory_type: str = "system"):

        memory = {
            "id": self.total_memories + 1,
            "organization_id": organization_id,
            "content": content,
            "memory_type": memory_type,
            "timestamp": datetime.utcnow().isoformat()
        }

        self.memory_store.append(memory)
        self.total_memories += 1

        return memory


    def retrieve(self, organization_id: str):

        return [
            memory for memory in self.memory_store
            if memory["organization_id"] == organization_id
        ]


    def get_status(self):

        return {
            "total_memories": self.total_memories,
            "manager_status": "ACTIVE"
        }


# REQUIRED GLOBAL INSTANCE
memory_manager = MemoryManager()