# app/control/control_engine.py

class ControlEngine:

    def __init__(self):
        self.waiting = False
        self.decision = None

    # ==========================
    # STATE CONTROL
    # ==========================
    def set_waiting(self, value: bool):
        self.waiting = value
        self.decision = None

    def is_waiting(self):
        return self.waiting

    def set_decision(self, decision: str):
        self.decision = decision
        self.waiting = False

    def get_decision(self):
        return self.decision


# ✅ GLOBAL INSTANCE
control_engine = ControlEngine()