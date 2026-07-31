from dataclasses import dataclass
from typing import Optional


@dataclass
class Strategy:
    strategy_id: str
    name: str
    parent: Optional[str] = None
    mutation_rate: float = 0.0

    def to_dict(self):
        return {
            "id": self.strategy_id,
            "name": self.name,
            "parent": self.parent,
            "mutation_rate": self.mutation_rate,
        }