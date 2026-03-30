# app/distributed/collective_intelligence_engine.py

import time


class CollectiveIntelligenceEngine:

    def __init__(self):

        self.agents = {}
        self.shared_insights = []
        self.knowledge_broadcasts = []

        print("[COLLECTIVE INTELLIGENCE] Engine initialized")

    # ------------------------------------------------
    # Register Agent
    # ------------------------------------------------

    def register_agent(self, agent_id, capabilities=None):

        if agent_id not in self.agents:

            self.agents[agent_id] = {
                "capabilities": capabilities or [],
                "last_seen": time.time(),
                "contributions": 0
            }

            print(f"[COLLECTIVE INTELLIGENCE] Agent registered: {agent_id}")

    # ------------------------------------------------
    # Broadcast Knowledge
    # ------------------------------------------------

    def broadcast_knowledge(self, knowledge_entry):

        broadcast = {
            "timestamp": time.time(),
            "knowledge": knowledge_entry
        }

        self.knowledge_broadcasts.append(broadcast)

        print("[COLLECTIVE INTELLIGENCE] Knowledge broadcasted")

    # ------------------------------------------------
    # Share Insight
    # ------------------------------------------------

    def share_insight(self, agent_id, insight):

        entry = {
            "agent": agent_id,
            "insight": insight,
            "timestamp": time.time()
        }

        self.shared_insights.append(entry)

        if agent_id in self.agents:
            self.agents[agent_id]["contributions"] += 1

        print(f"[COLLECTIVE INTELLIGENCE] Insight shared by {agent_id}")

    # ------------------------------------------------
    # Retrieve Collective Insights
    # ------------------------------------------------

    def get_collective_insights(self, goal=None):

        results = []

        for insight in self.shared_insights:

            if goal is None:
                results.append(insight)
            else:
                if goal.lower() in str(insight["insight"]).lower():
                    results.append(insight)

        print(f"[COLLECTIVE INTELLIGENCE] Retrieved {len(results)} insights")

        return results

    # ------------------------------------------------
    # Synchronize Agents
    # ------------------------------------------------

    def synchronize_agents(self):

        print("[COLLECTIVE INTELLIGENCE] Synchronizing agents")

        for agent in self.agents:

            self.agents[agent]["last_seen"] = time.time()

        return {
            "agents": len(self.agents),
            "insights": len(self.shared_insights),
            "broadcasts": len(self.knowledge_broadcasts)
        }

    # ------------------------------------------------
    # Stats
    # ------------------------------------------------

    def stats(self):

        return {
            "agents": len(self.agents),
            "insights": len(self.shared_insights),
            "broadcasts": len(self.knowledge_broadcasts)
        }


collective_intelligence_engine = CollectiveIntelligenceEngine()