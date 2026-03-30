# app/knowledge/global_knowledge_graph.py

import time
import uuid


class GlobalKnowledgeGraph:

    def __init__(self):

        # Node storage
        self.nodes = {}

        # Relationship storage
        self.edges = []

        print("[GLOBAL KNOWLEDGE GRAPH] Initialized")

    # ------------------------------------------------
    # Create Node
    # ------------------------------------------------

    def create_node(self, node_type, data):

        node_id = str(uuid.uuid4())

        node = {
            "id": node_id,
            "type": node_type,
            "data": data,
            "timestamp": time.time()
        }

        self.nodes[node_id] = node

        return node_id

    # ------------------------------------------------
    # Create Relationship
    # ------------------------------------------------

    def create_edge(self, source_id, relation, target_id):

        edge = {
            "source": source_id,
            "relation": relation,
            "target": target_id,
            "timestamp": time.time()
        }

        self.edges.append(edge)

    # ------------------------------------------------
    # Update Graph from Cognitive Loop
    # ------------------------------------------------

    def update_graph(self, knowledge):

        print("[GLOBAL KNOWLEDGE GRAPH] Updating graph...")

        goal = knowledge.get("goal")
        plan = knowledge.get("plan")
        results = knowledge.get("execution_results")
        world_state = knowledge.get("world_state")
        sector = knowledge.get("sector")
        human_feedback = knowledge.get("human_feedback")

        # --------------------------------
        # Goal Node
        # --------------------------------

        goal_id = None
        if goal:
            goal_id = self.create_node("goal", goal)

        # --------------------------------
        # Sector Node
        # --------------------------------

        sector_id = None
        if sector:
            sector_id = self.create_node("sector", {"name": sector})

            if goal_id:
                self.create_edge(goal_id, "belongs_to_sector", sector_id)

        # --------------------------------
        # Plan Node
        # --------------------------------

        plan_id = None
        if plan:
            plan_id = self.create_node("plan", {"steps": plan})

            if goal_id:
                self.create_edge(goal_id, "generates_plan", plan_id)

        # --------------------------------
        # Execution Results
        # --------------------------------

        if results and plan_id:

            for r in results:

                action_id = self.create_node("action", r)

                self.create_edge(plan_id, "executes", action_id)

        # --------------------------------
        # World State
        # --------------------------------

        if world_state:

            world_id = self.create_node("world_state", world_state)

            if goal_id:
                self.create_edge(goal_id, "affects_world", world_id)

        # --------------------------------
        # Human Feedback
        # --------------------------------

        if human_feedback:

            human_node = self.create_node("human_feedback", {
                "decision": human_feedback
            })

            if plan_id:
                self.create_edge(human_node, "approves_plan", plan_id)

        print("[GLOBAL KNOWLEDGE GRAPH] Nodes:", len(self.nodes))
        print("[GLOBAL KNOWLEDGE GRAPH] Edges:", len(self.edges))

    # ------------------------------------------------
    # Query Knowledge
    # ------------------------------------------------

    def query(self, node_type=None):

        results = []

        for node in self.nodes.values():

            if node_type is None or node["type"] == node_type:
                results.append(node)

        return results

    # ------------------------------------------------
    # Get Graph Stats
    # ------------------------------------------------

    def stats(self):

        return {
            "nodes": len(self.nodes),
            "edges": len(self.edges)
        }


# Singleton instance
global_knowledge_graph = GlobalKnowledgeGraph()