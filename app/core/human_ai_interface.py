# app/core/human_ai_interface.py

import time
import json
from app.core.memory_retrieval_engine import memory_retrieval_engine

class HumanAIInterface:
    """
    Human-AI Collaboration Interface
    Allows humans to review AI-generated plans, provide feedback, and
    log interactions for learning and transparency.
    """

    def __init__(self):
        # Feedback log: stores past human decisions for learning
        self.feedback_log = []

    def request_review(self, plan, goal=None, world_state=None, context=None):
        """
        Present AI plan to human for review.
        Returns:
            "approved" - if human approves plan
            "modify"   - if human wants modifications
            "rejected" - if human rejects plan
        """
        print("\n[HUMAN-AI INTERFACE] Plan ready for review:")
        print(json.dumps(plan, indent=2))

        if goal:
            print(f"[HUMAN-AI INTERFACE] Goal: {goal.get('name', 'unknown')}")
        if world_state:
            print(f"[HUMAN-AI INTERFACE] World State Snapshot: {world_state}")
        if context:
            print(f"[HUMAN-AI INTERFACE] Context Snapshot: {context}")

        # Simulate human input (replace with real UI in production)
        feedback = self._simulate_human_feedback(plan)

        # Log feedback
        self.log_feedback(plan, feedback)

        return feedback["decision"]

    def _simulate_human_feedback(self, plan):
        """
        Simulated human feedback for testing.
        You can replace this with actual UI input.
        """
        time.sleep(1)  # simulate human review delay

        # For demo, automatically approve small plans, request modify for large ones
        if len(plan) <= 5:
            decision = "approved"
        else:
            decision = "modify"

        feedback = {
            "decision": decision,
            "details": {"comment": "Simulated feedback based on plan length"},
            "timestamp": time.time()
        }
        print(f"[HUMAN-AI INTERFACE] Human feedback simulated: {decision}")
        return feedback

    def log_feedback(self, plan, feedback):
        """
        Log human feedback for future learning.
        """
        entry = {
            "plan": plan,
            "feedback": feedback,
            "memories": memory_retrieval_engine.retrieve({"plan": plan})
        }
        self.feedback_log.append(entry)
        print(f"[HUMAN-AI INTERFACE] Feedback logged. Total entries: {len(self.feedback_log)}")

    def get_feedback_log(self):
        """
        Return all logged human feedback.
        """
        return self.feedback_log


# Singleton instance for Cognitive Loop integration
human_ai_interface = HumanAIInterface()