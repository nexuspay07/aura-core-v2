import random
from app.learning.reinforcement_memory import reinforcement_memory


class ExperienceReplayEngine:

    def __init__(self):
        print("[EXPERIENCE REPLAY] Engine initialized")

    def sample_experiences(self, batch_size=5):

        memory = reinforcement_memory.experiences

        if len(memory) == 0:
            return []

        batch = random.sample(memory, min(batch_size, len(memory)))

        return batch

    def analyze_batch(self):

        batch = self.sample_experiences()

        if not batch:
            return None

        action_scores = {}

        for exp in batch:

            action = exp["action"]
            reward = exp["reward"]

            if action not in action_scores:
                action_scores[action] = 0

            action_scores[action] += reward

        return action_scores


experience_replay_engine = ExperienceReplayEngine()