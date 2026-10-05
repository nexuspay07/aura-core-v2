"""Strict provider schema for model-generatable Simulation V1 analysis."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any


SIMULATION_SCHEMA_NAME = "strategy_stress_test_result"


def simulation_model_schema(
    scenario_keys: Iterable[str],
    evidence_ids: Iterable[str],
) -> dict[str, Any]:
    """Build a deterministic schema constrained to caller-owned references."""

    scenarios = sorted(set(scenario_keys))
    evidence = sorted(set(evidence_ids))
    text = {"type": "string", "minLength": 1, "maxLength": 4000}
    finding = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "statement": text,
            "provenance": {
                "type": "string",
                "enum": ["SOURCE", "USER_SUPPLIED", "MODEL_GENERATED", "DERIVED"],
            },
            "evidence_refs": {
                "type": "array",
                "items": {"type": "string", "enum": evidence},
                "maxItems": 50,
                "uniqueItems": True,
            },
        },
        "required": ["statement", "provenance", "evidence_refs"],
    }
    findings = lambda required=False: {
        "type": "array",
        "items": finding,
        "minItems": 1 if required else 0,
        "maxItems": 50,
    }
    scenario = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "scenario_key": {"type": "string", "enum": scenarios},
            "elements_under_stress": findings(True),
            "plausible_effects": findings(True),
            "sensitivity": {"type": "string", "enum": ["LOW", "MODERATE", "HIGH"]},
            "constraint_conflicts": findings(),
            "risk_observations": findings(),
            "mitigation_observations": findings(),
            "phase_sensitivities": findings(),
            "upside_conditions": findings(),
            "downside_conditions": findings(),
            "change_condition_triggers": findings(),
        },
        "required": [
            "scenario_key", "elements_under_stress", "plausible_effects", "sensitivity",
            "constraint_conflicts", "risk_observations", "mitigation_observations",
            "phase_sensitivities", "upside_conditions", "downside_conditions",
            "change_condition_triggers",
        ],
    }
    properties = {
        "scenario_results": {
            "type": "array", "items": scenario,
            "minItems": len(scenarios), "maxItems": len(scenarios),
        },
        "cross_scenario_comparison": findings(True),
        "assumptions_used": findings(),
        "uncertainties": findings(True),
        "confidence": {"type": "string", "enum": ["LOW", "MODERATE", "HIGH"]},
        "confidence_rationale": {
            "type": "array", "items": text, "minItems": 1, "maxItems": 20,
        },
        "evidence_refs": {
            "type": "array",
            "items": {"type": "string", "enum": evidence},
            "maxItems": 50,
            "uniqueItems": True,
        },
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
        "required": list(properties),
    }
