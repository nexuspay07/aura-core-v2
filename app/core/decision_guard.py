class DecisionGuard:

    def __init__(self):
        self.history = []

    def record(self, action):
        self.history.append(action)

        if len(self.history) > 10:
            self.history.pop(0)

    def too_repetitive(self, action):

        recent = self.history[-5:]

        count = recent.count(action)

        if count >= 3:
            return True

        return False


decision_guard = DecisionGuard()