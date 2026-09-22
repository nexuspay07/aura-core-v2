from copy import deepcopy
from types import SimpleNamespace

import pytest

from app.intelligence_v2.model_provider import (
    MockModelProvider,
    OpenAIModelProvider,
    ProviderUnavailableError,
    UnconfiguredModelProvider,
    model_analysis_schema,
)


CUSTOM_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {"approach": {"type": "string"}},
    "required": ["approach"],
}


def test_default_request_preserves_exact_decision_schema_name_and_strict_mode():
    request = OpenAIModelProvider(api_key="offline").request_kwargs(system="system", payload={"x": 1})
    output_format = request["text"]["format"]
    assert output_format == {
        "type": "json_schema",
        "name": "model_analysis_result",
        "strict": True,
        "schema": model_analysis_schema(),
    }


def test_custom_schema_and_name_are_used_without_decision_schema_merging_or_mutation():
    original = deepcopy(CUSTOM_SCHEMA)
    request = OpenAIModelProvider(api_key="offline").request_kwargs(
        system="system", payload={}, output_schema=CUSTOM_SCHEMA, schema_name="strategy_result",
    )
    output_format = request["text"]["format"]
    assert output_format["schema"] == CUSTOM_SCHEMA
    assert output_format["schema"] != model_analysis_schema()
    assert output_format["name"] == "strategy_result"
    assert output_format["strict"] is True
    assert CUSTOM_SCHEMA == original


def test_sequential_default_custom_default_requests_do_not_leak_schema_state():
    provider = OpenAIModelProvider(api_key="offline")
    first = provider.request_kwargs(system="one", payload={})["text"]["format"]
    custom = provider.request_kwargs(system="two", payload={}, output_schema=CUSTOM_SCHEMA, schema_name="custom")["text"]["format"]
    third = provider.request_kwargs(system="three", payload={})["text"]["format"]
    assert first == third
    assert first["schema"] == model_analysis_schema()
    assert custom["schema"] == CUSTOM_SCHEMA and custom["name"] == "custom"


def test_generate_structured_forwards_custom_schema_without_extra_provider_calls(monkeypatch):
    captured = []

    class Responses:
        def create(self, **kwargs):
            captured.append(kwargs)
            return SimpleNamespace(
                status="completed", incomplete_details=None, error=None,
                output_text='{"approach":"Preserve constraints."}', output=[],
                usage=SimpleNamespace(input_tokens=1, output_tokens=2, output_tokens_details=None, total_tokens=3),
                _request_id="offline",
            )

    monkeypatch.setattr("openai.OpenAI", lambda **_: SimpleNamespace(responses=Responses()))
    provider = OpenAIModelProvider(api_key="offline", model_name="gpt-4o-mini")
    result, _ = provider.generate_structured(
        system="system", payload={"objective": "test"}, timeout_seconds=10,
        output_schema=CUSTOM_SCHEMA, schema_name="strategy_result",
    )
    assert result == {"approach": "Preserve constraints."}
    assert len(captured) == 1
    assert captured[0]["text"]["format"]["schema"] == CUSTOM_SCHEMA
    assert captured[0]["text"]["format"]["name"] == "strategy_result"


def test_existing_generate_structured_call_uses_decision_defaults(monkeypatch):
    captured = []

    class Responses:
        def create(self, **kwargs):
            captured.append(kwargs)
            return SimpleNamespace(
                status="completed", incomplete_details=None, error=None,
                output_text='{"problem_summary":"ok"}', output=[],
                usage=SimpleNamespace(input_tokens=1, output_tokens=1, output_tokens_details=None, total_tokens=2),
                _request_id="offline",
            )

    monkeypatch.setattr("openai.OpenAI", lambda **_: SimpleNamespace(responses=Responses()))
    OpenAIModelProvider(api_key="offline").generate_structured(
        system="system", payload={}, timeout_seconds=10,
    )
    assert len(captured) == 1
    output_format = captured[0]["text"]["format"]
    assert output_format["schema"] == model_analysis_schema()
    assert output_format["name"] == "model_analysis_result"
    assert output_format["strict"] is True


def test_mock_provider_accepts_expanded_protocol_and_keeps_one_call():
    provider = MockModelProvider({"approach": "Preserve constraints."})
    result, _ = provider.generate_structured(
        system="system", payload={}, timeout_seconds=10,
        output_schema=CUSTOM_SCHEMA, schema_name="strategy_result",
    )
    assert result["approach"] == "Preserve constraints."
    assert provider.calls == 1


def test_unconfigured_provider_accepts_expanded_protocol_and_preserves_failure():
    with pytest.raises(ProviderUnavailableError, match="configured"):
        UnconfiguredModelProvider().generate_structured(
            system="system", payload={}, timeout_seconds=10,
            output_schema=CUSTOM_SCHEMA, schema_name="strategy_result",
        )


@pytest.mark.parametrize("name", ["", "contains spaces", "unsafe!", "x" * 65])
def test_invalid_schema_names_are_rejected(name):
    with pytest.raises(ValueError, match="schema_name"):
        OpenAIModelProvider(api_key="offline").request_kwargs(
            system="system", payload={}, output_schema=CUSTOM_SCHEMA, schema_name=name,
        )


def test_custom_schema_requires_dictionary_and_generic_name_is_safe():
    provider = OpenAIModelProvider(api_key="offline")
    with pytest.raises(ValueError, match="output_schema"):
        provider.request_kwargs(system="system", payload={}, output_schema="not-a-schema")
    output_format = provider.request_kwargs(system="system", payload={}, output_schema=CUSTOM_SCHEMA)["text"]["format"]
    assert output_format["name"] == "structured_result"


def test_model_timeout_and_selection_configuration_are_unchanged():
    provider = OpenAIModelProvider(api_key="offline", model_name="gpt-5.1")
    request = provider.request_kwargs(system="system", payload={}, output_schema=CUSTOM_SCHEMA, schema_name="custom")
    assert request["model"] == "gpt-5.1"
    assert request["reasoning"] == {"effort": provider.reasoning_effort}
