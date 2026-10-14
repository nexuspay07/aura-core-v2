from app.simulation.model_schema import (
    MAX_ASSUMPTIONS_USED,
    MAX_CONFIDENCE_RATIONALE,
    MAX_MODEL_TEXT_LENGTH,
    MAX_OPTIONAL_FINDINGS,
    MAX_REQUIRED_FINDINGS,
    simulation_model_schema,
)


_SUPPORTED_SCHEMA_KEYWORDS = {
    "additionalProperties",
    "enum",
    "items",
    "maxItems",
    "maxLength",
    "minItems",
    "minLength",
    "properties",
    "required",
    "type",
}


def _assert_supported_schema(schema):
    assert isinstance(schema, dict)
    assert set(schema).issubset(_SUPPORTED_SCHEMA_KEYWORDS)
    if schema.get("type") == "object":
        assert schema.get("additionalProperties") is False
        for child in schema.get("properties", {}).values():
            _assert_supported_schema(child)
    if schema.get("type") == "array":
        _assert_supported_schema(schema["items"])


def test_provider_schema_recursively_uses_supported_openai_strict_subset():
    schema = simulation_model_schema(("unexpected_expense",), ("evidence-1",))

    _assert_supported_schema(schema)
    assert "uniqueItems" not in repr(schema)


def test_provider_schema_with_no_evidence_requires_empty_reference_arrays():
    schema = simulation_model_schema(("unexpected_expense",), ())
    finding_refs = schema["properties"]["uncertainties"]["items"]["properties"]["evidence_refs"]
    result_refs = schema["properties"]["evidence_refs"]

    _assert_supported_schema(schema)
    assert finding_refs == {"type": "array", "items": {"type": "string"}, "maxItems": 0}
    assert result_refs == {"type": "array", "items": {"type": "string"}, "maxItems": 0}
    assert "enum" not in finding_refs["items"] and "enum" not in result_refs["items"]


def test_provider_schema_enforces_concise_generation_without_weakening_shape():
    schema = simulation_model_schema(("one", "two"), ("evidence-1",))
    properties = schema["properties"]
    scenario = properties["scenario_results"]["items"]["properties"]

    assert scenario["elements_under_stress"]["maxItems"] == MAX_REQUIRED_FINDINGS
    assert scenario["plausible_effects"]["maxItems"] == MAX_REQUIRED_FINDINGS
    assert scenario["risk_observations"]["maxItems"] == MAX_OPTIONAL_FINDINGS
    assert properties["assumptions_used"]["maxItems"] == MAX_ASSUMPTIONS_USED
    assert properties["confidence_rationale"]["maxItems"] == MAX_CONFIDENCE_RATIONALE
    assert scenario["elements_under_stress"]["items"]["properties"]["statement"]["maxLength"] == MAX_MODEL_TEXT_LENGTH
    _assert_supported_schema(schema)
    assert "uniqueItems" not in repr(schema)
