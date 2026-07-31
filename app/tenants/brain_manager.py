# app/tenants/brain_manager.py

from threading import Lock
from typing import Any, Dict, List


class BrainManager:
    """
    Central Brain Manager.

    Responsible for managing the active AI brain for each tenant.

    Future Responsibilities:
    - Load tenant memory
    - Load vector databases
    - Load knowledge graphs
    - Load tool registry
    - Load LLM adapters
    - Cache tenant brains
    - Unload inactive brains
    """

    def __init__(self):
        self.active_brains: Dict[str, Dict[str, Any]] = {}
        self._lock = Lock()

    # ==========================================================
    # LOAD BRAIN
    # ==========================================================

    def get_brain(self, tenant_id: str) -> Dict[str, Any]:

        with self._lock:

            if tenant_id not in self.active_brains:

                self.active_brains[tenant_id] = {

                    "tenant_id": tenant_id,

                    "status": "active",

                    "memory_loaded": True,

                    "knowledge_loaded": True,

                    "vector_loaded": True,

                    "tool_registry_loaded": True,

                    "llm_loaded": True,
                }

            return self.active_brains[tenant_id]

    # ==========================================================
    # UNLOAD
    # ==========================================================

    def unload_brain(self, tenant_id: str) -> bool:

        with self._lock:

            return self.active_brains.pop(tenant_id, None) is not None

    # ==========================================================
    # EXISTS
    # ==========================================================

    def brain_exists(self, tenant_id: str) -> bool:

        return tenant_id in self.active_brains

    # ==========================================================
    # LIST
    # ==========================================================

    def list_loaded_brains(self) -> List[Dict[str, Any]]:

        return list(self.active_brains.values())

    # ==========================================================
    # COUNT
    # ==========================================================

    def total_loaded_brains(self) -> int:

        return len(self.active_brains)

    # ==========================================================
    # CLEAR CACHE
    # ==========================================================

    def clear(self):

        with self._lock:
            self.active_brains.clear()


brain_manager = BrainManager()