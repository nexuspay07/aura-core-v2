class ConversationMemory:
    def __init__(self):
        self.sessions = {}
        self.user_profiles = {}

    # -----------------------------
    # SESSION HISTORY
    # -----------------------------
    def get_history(self, session_id: str):
        return self.sessions.get(session_id, [])

    def add_message(self, session_id: str, role: str, content: str):
        if session_id not in self.sessions:
            self.sessions[session_id] = []

        self.sessions[session_id].append({
            "role": role,
            "content": content
        })

    def clear_session(self, session_id: str):
        self.sessions[session_id] = []

    # -----------------------------
    # USER PROFILE MEMORY
    # -----------------------------
    def get_profile(self, session_id: str):
        return self.user_profiles.get(session_id, {
            "preferred_risk": None,
            "preferred_budget": None,
            "preferred_market": None,
            "preferred_domain": None
        })

    def update_profile(self, session_id: str, preferences: dict, domain: str | None = None):
        profile = self.get_profile(session_id)

        if "risk_tolerance" in preferences:
            if preferences["risk_tolerance"] <= 0.3:
                profile["preferred_risk"] = "low"
            elif preferences["risk_tolerance"] >= 0.7:
                profile["preferred_risk"] = "high"
            else:
                profile["preferred_risk"] = "balanced"

        if "budget" in preferences:
            profile["preferred_budget"] = preferences["budget"]

        if "market" in preferences:
            profile["preferred_market"] = preferences["market"]

        if domain:
            profile["preferred_domain"] = domain

        self.user_profiles[session_id] = profile

    def clear_profile(self, session_id: str):
        self.user_profiles[session_id] = {
            "preferred_risk": None,
            "preferred_budget": None,
            "preferred_market": None,
            "preferred_domain": None
        }

    def reset_all(self, session_id: str):
        self.clear_session(session_id)
        self.clear_profile(session_id)


conversation_memory = ConversationMemory()