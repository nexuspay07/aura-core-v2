class ConversationMemoryEngine:
    """
    Phase 69

    Maintains short-term conversation memory for
    every user session.
    """

    def __init__(self):
        self.sessions = {}

    def save_message(
        self,
        session_id,
        role,
        message
    ):

        if session_id not in self.sessions:
            self.sessions[session_id] = []

        self.sessions[session_id].append({
            "role": role,
            "message": message
        })

        # keep only the latest 20 messages
        self.sessions[session_id] = (
            self.sessions[session_id][-20:]
        )

    def get_history(
        self,
        session_id
    ):

        return self.sessions.get(
            session_id,
            []
        )

    def clear(
        self,
        session_id
    ):

        self.sessions.pop(
            session_id,
            None
        )


conversation_memory_engine = (
    ConversationMemoryEngine()
)