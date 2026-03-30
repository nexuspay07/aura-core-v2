# app/strategies/strategy_model.py

from dataclasses import dataclass
from typing import Dict


@dataclass
class Strategy:
    name: str
    parameters: Dict
    fitness: float = 0.0