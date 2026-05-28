import json
import os
import threading
import time

print(">>> LOADING MEMORY ENGINE FROM:", __file__)


class MemoryEngine:

    def __init__(self):

        self.lock = threading.Lock()

        self.short_term_memory = []
        self.long_term_memory = []

        BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

        self.memory_path = os.path.join(BASE_DIR, "memory")

        self.short_term_file = os.path.join(self.memory_path, "short_term.json")
        self.long_term_file = os.path.join(self.memory_path, "long_term.json")

        self._initialize_files()
        self._load_memory()

        print("[MEMORY ENGINE] Persistent memory initialized")

    # -------------------------
    # FILE INIT
    # -------------------------

    def _initialize_files(self):

        if not os.path.exists(self.memory_path):
            os.makedirs(self.memory_path)
            print("[MEMORY ENGINE] Created memory folder")

        if not os.path.exists(self.short_term_file):
            with open(self.short_term_file, "w") as f:
                json.dump([], f)

        if not os.path.exists(self.long_term_file):
            with open(self.long_term_file, "w") as f:
                json.dump([], f)

    # -------------------------
    # LOAD
    # -------------------------

    def _load_memory(self):

        try:

            with open(self.short_term_file, "r") as f:
                self.short_term_memory = json.load(f)

            with open(self.long_term_file, "r") as f:
                self.long_term_memory = json.load(f)

            print(f"[MEMORY ENGINE] Loaded {len(self.short_term_memory)} short-term memories")
            print(f"[MEMORY ENGINE] Loaded {len(self.long_term_memory)} long-term memories")

        except Exception as e:

            print("[MEMORY ENGINE LOAD ERROR]", e)

    # -------------------------
    # SAVE
    # -------------------------

    def _save_short_term(self):

        with open(self.short_term_file, "w") as f:
            json.dump(self.short_term_memory, f, indent=2)

    def _save_long_term(self):

        with open(self.long_term_file, "w") as f:
            json.dump(self.long_term_memory, f, indent=2)

    # -------------------------
    # STORE SHORT TERM
    # -------------------------

    def store_short_term(self, memory):

        with self.lock:

            memory["timestamp"] = time.time()
            memory["access_count"] = 0

            self.short_term_memory.append(memory)

            self._save_short_term()

            print(f"[MEMORY] Stored short-term memory #{len(self.short_term_memory)}")

    # -------------------------
    # STORE LONG TERM
    # -------------------------

    def store_long_term(self, memory):

        with self.lock:

            self.long_term_memory.append(memory)

            self._save_long_term()

            print(f"[MEMORY] Promoted to LONG-TERM memory #{len(self.long_term_memory)}")

    # -------------------------
    # CONSOLIDATION
    # -------------------------

    def consolidate_memory(self):

        with self.lock:

            promoted = 0

            for memory in self.short_term_memory:

                if self._is_important(memory):

                    if memory not in self.long_term_memory:

                        self.long_term_memory.append(memory)

                        promoted += 1

                        print("[MEMORY CONSOLIDATION] Promoted:", memory.get("type"))

            if promoted > 0:
                self._save_long_term()

    # -------------------------
    # IMPORTANCE CHECK
    # -------------------------

    def _is_important(self, memory):

        if memory.get("type") == "goal":
            return True

        if memory.get("access_count", 0) > 3:
            return True

        return False

    # -------------------------
    # NEW: MEMORY RETRIEVAL INTELLIGENCE
    # -------------------------

    def retrieve_relevant(self, context, limit=5):

        with self.lock:

            scored_memories = []

            all_memories = self.short_term_memory + self.long_term_memory

            for memory in all_memories:

                score = self._calculate_relevance(memory, context)

                if score > 0:

                    scored_memories.append((score, memory))

                    memory["access_count"] += 1

            scored_memories.sort(key=lambda x: x[0], reverse=True)

            results = [memory for score, memory in scored_memories[:limit]]

            print(f"[MEMORY RETRIEVAL] Retrieved {len(results)} relevant memories")

            return results

    # -------------------------
    # RELEVANCE SCORING
    # -------------------------

    def _calculate_relevance(self, memory, context):

        score = 0

        context_str = str(context).lower()
        memory_str = str(memory).lower()

        # keyword match scoring
        for word in context_str.split():

            if word in memory_str:
                score += 1

        # recent memory bonus
        age = time.time() - memory.get("timestamp", time.time())

        if age < 300:
            score += 2

        # access frequency bonus
        score += memory.get("access_count", 0)

        return score

    # -------------------------
    # GETTERS
    # -------------------------

    def get_short_term(self):

        return self.short_term_memory

    def get_long_term(self):

        return self.long_term_memory

    # -------------------------
    # STATUS
    # -------------------------

    def get_status(self):

        return {
            "short_term_count": len(self.short_term_memory),
            "long_term_count": len(self.long_term_memory),
            "total_memories": len(self.short_term_memory)
            + len(self.long_term_memory)
        }


memory_engine = MemoryEngine()