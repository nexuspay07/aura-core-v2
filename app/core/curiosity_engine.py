# app/core/curiosity_engine.py

from app.core.resource_intelligence_engine import resource_intelligence_engine

class CuriosityEngine:
    """
    Phase 209.6 — Curiosity / Exploration Engine
    Responsible for generating exploratory insights and detecting new opportunities
    """

    def __init__(self):
        # Use the resource intelligence engine object, not callable
        self.resource_engine = resource_intelligence_engine

    def explore(self, goal, context, memories, world_state):
        """
        Analyze current goal, context, memories, and world state
        to generate exploratory insights and curiosity-driven actions.
        """
        # Example logic (replace with real AI/heuristic exploration)
        new_opportunities = []

        # Simple heuristic: if memory is empty, suggest exploration
        if not memories:
            new_opportunities.append("Collect additional data to improve decision-making")

        # Check for high resource usage as an exploration trigger
        resources = self.resource_engine.get_current_resources()
        if resources.get("memory", 0) > 70:
            new_opportunities.append("Optimize memory usage")

        # Combine world state insights
        if world_state.get("profit", 0) < 100:
            new_opportunities.append("Explore cost reduction strategies")

        curiosity_score = min(1.0, len(new_opportunities) * 0.25)  # simple normalized score

        return {
            "new_opportunities": new_opportunities,
            "curiosity_score": curiosity_score
        }