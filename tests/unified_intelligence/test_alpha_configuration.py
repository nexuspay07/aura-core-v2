from pathlib import Path

from app.unified_intelligence.contracts import ModelRequest
from app.unified_intelligence.model_router import OpenAILanguageModelProvider


def test_general_provider_configuration_is_bounded_and_store_is_disabled(monkeypatch):
    provider = OpenAILanguageModelProvider(api_key="offline", model_name="gpt-5.1")
    monkeypatch.setenv("AURA_GENERAL_MAX_OUTPUT_TOKENS", "99999")
    monkeypatch.setenv("AURA_GENERAL_REASONING_EFFORT", "invalid")
    kwargs = provider.request_kwargs(ModelRequest("natural_text_generation", "system", "prompt"))
    assert kwargs["max_output_tokens"] == 3000
    assert kwargs["reasoning"] == {"effort": "low"}
    assert kwargs["store"] is False
    monkeypatch.setenv("AURA_GENERAL_MAX_OUTPUT_TOKENS", "1")
    assert provider.max_output_tokens() == 256


def test_production_start_command_targets_the_real_asgi_application():
    procfile = Path(__file__).parents[2] / "Procfile"
    assert "uvicorn app.main:app" in procfile.read_text(encoding="utf-8")
