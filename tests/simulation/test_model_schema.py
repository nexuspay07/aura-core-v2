from app.simulation.model_schema import simulation_model_schema


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
