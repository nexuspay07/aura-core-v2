"""Strict provider schema for model-generatable Strategy content only."""

from __future__ import annotations

from typing import Any


STRATEGY_SCHEMA_NAME = "strategy_result"


def strategy_model_schema() -> dict[str, Any]:
    string = lambda maximum: {"type": "string", "maxLength": maximum}
    strings = lambda count, length=240: {
        "type": "array", "items": string(length), "maxItems": count,
    }
    phase = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "order": {"type": "integer", "minimum": 1},
            "name": string(120),
            "purpose": string(360),
            "focus_areas": strings(5, 220),
            "milestone_intent": {"type": ["string", "null"], "maxLength": 280},
        },
        "required": ["order", "name", "purpose", "focus_areas", "milestone_intent"],
    }
    mitigation = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "risk_index": {"type": "integer", "minimum": 0},
            "mitigation": string(300),
        },
        "required": ["risk_index", "mitigation"],
    }
    properties = {
        "approach": string(700),
        "phases": {"type": "array", "items": phase, "minItems": 1, "maxItems": 6},
        "risk_mitigations": {"type": "array", "items": mitigation, "maxItems": 8},
        "success_measures": strings(6, 300),
        "assumptions": strings(4, 260),
        "uncertainties": strings(6, 260),
        "change_conditions": strings(6, 300),
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
        "required": list(properties),
    }
