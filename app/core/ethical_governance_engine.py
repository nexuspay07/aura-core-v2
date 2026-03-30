# app/core/ethical_governance_engine.py

class EthicalGovernanceEngine:
    """
    Phase 216 — Ethical Governance Layer
    Evaluates plans for compliance with ethical and regulatory rules.
    """

    def __init__(self):
        # Example: you can populate with real ethical rules later
        self.rules = [
            "avoid_harm",
            "ensure_transparency",
            "respect_privacy",
            "resource_fairness"
        ]

    def approve_plan(self, plan):
        """
        Approve or reject a plan based on ethical rules.
        Returns True if the plan passes all checks, False otherwise.
        """

        if not plan:
            print("[ETHICAL GOVERNANCE] No plan provided — rejected")
            return False

        # Example checks (can be expanded)
        for step in plan:
            if "illegal" in str(step).lower():
                print("[ETHICAL GOVERNANCE] Plan contains illegal step — rejected")
                return False

        # If all checks pass
        print("[ETHICAL GOVERNANCE] Plan approved")
        return True

    def add_rule(self, rule):
        """Add a new ethical rule dynamically"""
        if rule not in self.rules:
            self.rules.append(rule)
            print(f"[ETHICAL GOVERNANCE] Rule added: {rule}")

    def list_rules(self):
        """Return the current set of ethical rules"""
        return self.rules


# Instantiate the engine
ethical_governance_engine = EthicalGovernanceEngine()