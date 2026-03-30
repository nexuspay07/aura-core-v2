# app/control/control_engine.py

import time

class ControlEngine:
    def __init__(self):
        self.state = "idle"   # idle | waiting | approved | rejected

    def wait_for_decision(self):
        self.state = "waiting"

        while self.state == "waiting":
            time.sleep(0.5)

        return self.state

    def approve(self):
        self.state = "approved"

    def reject(self):
        self.state = "rejected"

    def reset(self):
        self.state = "idle"


control_engine = ControlEngine()