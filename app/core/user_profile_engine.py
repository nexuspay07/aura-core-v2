import json
import os


class UserProfileEngine:
    def __init__(self):
        self.file_path = "user_profiles.json"
        self.profiles = self.load_profiles()

    def load_profiles(self):
        if not os.path.exists(self.file_path):
            return {}

        try:
            with open(self.file_path, "r", encoding="utf-8") as file:
                return json.load(file)
        except Exception:
            return {}

    def save_profiles(self):
        with open(self.file_path, "w", encoding="utf-8") as file:
            json.dump(self.profiles, file, indent=4)

    def get_profile(self, user_id: str):
        if user_id not in self.profiles:
            self.profiles[user_id] = {
                "preferred_risk": None,
                "preferred_budget": None,
                "preferred_domain": None,
                "interaction_count": 0
            }
            self.save_profiles()

        return self.profiles[user_id]

    def update_profile(self, user_id: str, scenario: dict, domain: str):
        profile = self.get_profile(user_id)

        profile["interaction_count"] += 1

        risk = scenario.get("risk_tolerance", 0.5)

        if risk <= 0.3:
            profile["preferred_risk"] = "low"
        elif risk >= 0.7:
            profile["preferred_risk"] = "high"
        else:
            profile["preferred_risk"] = "medium"

        profile["preferred_budget"] = scenario.get("budget", 10000)
        profile["preferred_domain"] = domain

        self.profiles[user_id] = profile
        self.save_profiles()

        return profile

    def reset_profile(self, user_id: str):
        if user_id in self.profiles:
            del self.profiles[user_id]
            self.save_profiles()

        return {
            "preferred_risk": None,
            "preferred_budget": None,
            "preferred_domain": None,
            "interaction_count": 0
        }


user_profile_engine = UserProfileEngine()