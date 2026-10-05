"""Stable JSON-compatible serialization for canonical Simulation contracts."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from enum import Enum
import json
from typing import Any


def simulation_to_dict(value: object) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return {
            item.name: simulation_to_dict(getattr(value, item.name))
            for item in fields(value)
        }
    if isinstance(value, tuple):
        return [simulation_to_dict(item) for item in value]
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise TypeError(f"Unsupported canonical Simulation value: {type(value).__name__}")


def simulation_to_json(value: object) -> str:
    return json.dumps(
        simulation_to_dict(value),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
