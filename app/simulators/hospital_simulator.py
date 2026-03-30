# app/simulators/hospital_simulator.py


class HospitalSimulator:
    """
    Simulates a hospital environment for AURA AI testing.
    """

    MAX_CAPACITY = 150
    MIN_CAPACITY = 20

    def __init__(self):

        self.state = {
            "patients": 40,
            "staff": 12,
            "capacity": 100,
            "wait_time": 20
        }

        print("[HOSPITAL SIMULATOR] Initialized")

    def get_state(self):
        return self.state.copy()

    def apply_action(self, action):

        if action == "open_beds":

            if self.state["capacity"] < self.MAX_CAPACITY:
                self.state["capacity"] += 10
            else:
                print("[SIMULATOR] Capacity already at maximum")

        elif action == "allocate_staff":

            self.state["staff"] += 1

            if self.state["wait_time"] > 5:
                self.state["wait_time"] -= 5

        elif action == "optimize_triage":

            if self.state["wait_time"] > 3:
                self.state["wait_time"] -= 3

        elif action == "do_nothing":
            pass

        # Natural patient flow simulation
        self._simulate_patient_flow()

        return {"status": "action_applied", "action": action}

    def _simulate_patient_flow(self):

        # New patients arrive
        self.state["patients"] += 2

        # Staff treat patients
        treated = min(self.state["staff"], self.state["patients"])
        self.state["patients"] -= treated

        # Wait time increases if overloaded
        if self.state["patients"] > self.state["capacity"]:
            self.state["wait_time"] += 5

        # Wait time slowly improves if under capacity
        elif self.state["wait_time"] > 0:
            self.state["wait_time"] -= 1

        # Prevent negative values
        self.state["patients"] = max(0, self.state["patients"])
        self.state["wait_time"] = max(0, self.state["wait_time"])


# Singleton
hospital = HospitalSimulator()