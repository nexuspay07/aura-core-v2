# app/security/identity_engine.py

class IdentityEngine:
    def __init__(self):
        self.agents = {}  # agent_id -> info
        self.users = {}   # user_id -> info

    def register_agent(self, agent_id, capabilities=None, token=None):
        self.agents[agent_id] = {
            "capabilities": capabilities or [],
            "token": token or "DEFAULT_TOKEN"
        }

    def verify_agent(self, agent_id):
        return agent_id in self.agents

    def verify_agent_token(self, agent_id, token):
        agent = self.agents.get(agent_id)
        return agent is not None and agent.get("token") == token

    def get_role(self, entity_id):
        # Simplified: return role for security checks
        agent = self.agents.get(entity_id)
        if agent:
            return "agent"
        user = self.users.get(entity_id)
        if user:
            return user.get("role", "user")
        return None

    def register_user(self, user_id, role="user", credentials=None):
        self.users[user_id] = {"role": role, "credentials": credentials or "DEFAULT_CRED"}

    def verify_user(self, user_id):
        return user_id in self.users

    def verify_user_credentials(self, user_id, credentials):
        user = self.users.get(user_id)
        return user is not None and user.get("credentials") == credentials


# Global instance
identity_engine = IdentityEngine()