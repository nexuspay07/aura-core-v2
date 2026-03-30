# app/core/sector_intelligence_engine.py

class SectorIntelligenceEngine:

    def __init__(self):

        self.sectors = {
            "finance": self.finance_module,
            "healthcare": self.healthcare_module,
            "logistics": self.logistics_module,
            "infrastructure": self.infrastructure_module
        }

    def detect_sector(self, goal, context):

        goal_text = str(goal).lower()

        if "finance" in goal_text or "market" in goal_text:
            return "finance"

        if "health" in goal_text or "medical" in goal_text:
            return "healthcare"

        if "logistics" in goal_text or "supply" in goal_text:
            return "logistics"

        if "traffic" in goal_text or "energy" in goal_text:
            return "infrastructure"

        return "general"

    def apply_sector_logic(self, sector, context, world_state):

        if sector in self.sectors:
            return self.sectors[sector](context, world_state)

        return {"sector": "general", "insight": "no sector specialization"}

    def finance_module(self, context, world_state):

        insight = {
            "sector": "finance",
            "risk_score": world_state.get("profit", 0) / 1000
        }

        print("[SECTOR INTELLIGENCE] Finance insight generated")

        return insight

    def healthcare_module(self, context, world_state):

        insight = {
            "sector": "healthcare",
            "optimization": "patient workflow improvement"
        }

        print("[SECTOR INTELLIGENCE] Healthcare insight generated")

        return insight

    def logistics_module(self, context, world_state):

        insight = {
            "sector": "logistics",
            "optimization": "supply chain efficiency improvement"
        }

        print("[SECTOR INTELLIGENCE] Logistics insight generated")

        return insight

    def infrastructure_module(self, context, world_state):

        insight = {
            "sector": "infrastructure",
            "optimization": "traffic and energy balancing"
        }

        print("[SECTOR INTELLIGENCE] Infrastructure insight generated")

        return insight


sector_intelligence_engine = SectorIntelligenceEngine()