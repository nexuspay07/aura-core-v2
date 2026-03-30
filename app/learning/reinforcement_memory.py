class ReinforcementMemory:

    def __init__(self):

        # stores all learning experiences
        self.experiences = []

    def store_experience(self, state, action, reward):

        experience = {
            "state": state,
            "action": action,
            "reward": reward
        }

        self.experiences.append(experience)

    def get_all_experiences(self):

        return self.experiences


reinforcement_memory = ReinforcementMemory()