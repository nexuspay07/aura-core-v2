from datetime import datetime


class IntelligenceExpansionEngine:

    def __init__(self):

        self.expansion_level = 1
        self.total_expansions = 0
        self.last_expansion_time = None

        self.expansion_history = []

    def expand(self):

        self.expansion_level += 1
        self.total_expansions += 1

        self.last_expansion_time = datetime.utcnow().isoformat()

        expansion_record = {
            "expansion_level": self.expansion_level,
            "timestamp": self.last_expansion_time
        }

        self.expansion_history.append(expansion_record)

        print(f"[EXPANSION] Intelligence expanded to level {self.expansion_level}")

        return expansion_record

    def get_status(self):

        return {
            "expansion_level": self.expansion_level,
            "total_expansions": self.total_expansions,
            "last_expansion_time": self.last_expansion_time
        }


# global instance
intelligence_expansion_engine = IntelligenceExpansionEngine()