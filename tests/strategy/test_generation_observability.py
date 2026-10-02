import logging

import pytest

from app.intelligence_v2.model_provider import (
    InvalidModelResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from app.strategy.orchestrator import StrategyGenerationError, StrategyOrchestrator
from app.strategy.quality import StrategyQualityError
from app.strategy.validation import StrategyValidationError
from tests.strategy.test_orchestrator import RecordingProvider, minimal_input, valid_model_output


PRIVATE_MARKERS = (
    "PRIVATE DECISION TEXT",
    "PRIVATE GENERATED APPROACH",
    "PRIVATE STRATEGY PHASE",
)


def messages(caplog):
    return [record.message for record in caplog.records if "strategy_generation_stage=" in record.message]


def private_input():
    return minimal_input(
        objective="PRIVATE DECISION TEXT",
        chosen_direction="Preserve private savings",
    )


def private_quality_failure():
    return valid_model_output(
        approach="Preserve, private savings!!!",
        phases=[{
            "order": 1,
            "name": "PRIVATE STRATEGY PHASE",
            "purpose": "Keep private content out of logs.",
            "focus_areas": [],
            "milestone_intent": None,
        }],
    )


def test_first_quality_failure_logs_safe_code_and_existing_repair_succeeds(caplog):
    caplog.set_level(logging.WARNING, logger="uvicorn.error")
    provider = RecordingProvider(private_quality_failure(), valid_model_output())

    result = StrategyOrchestrator(provider).generate(private_input())

    logs = messages(caplog)
    assert result.approach and len(provider.calls) == 2
    assert any(
        "strategy_generation_stage=attempt_failed attempt=1 max_attempts=2 "
        "category=quality_validation quality_codes=strategy.approach_restates_direction "
        "repair_next=true repair_exhausted=false provider_calls=1" in line
        for line in logs
    )
    assert any("strategy_generation_stage=attempt_started attempt=2" in line and "repair_attempt=true" in line for line in logs)
    assert not any("strategy_generation_stage=terminal_failure" in line for line in logs)
    assert not any(marker in " ".join(logs) for marker in PRIVATE_MARKERS)


def test_second_quality_failure_logs_terminal_exhausted_state(caplog):
    caplog.set_level(logging.WARNING, logger="uvicorn.error")
    provider = RecordingProvider(private_quality_failure())

    with pytest.raises(StrategyQualityError):
        StrategyOrchestrator(provider).generate(private_input())

    logs = messages(caplog)
    assert len(provider.calls) == 2
    assert any(
        "strategy_generation_stage=terminal_failure attempt=2 max_attempts=2 "
        "category=quality_validation quality_codes=strategy.approach_restates_direction "
        "repair_next=false repair_exhausted=true provider_calls=2" in line
        for line in logs
    )
    assert not any(marker in " ".join(logs) for marker in PRIVATE_MARKERS)


@pytest.mark.parametrize(
    "failure,category,calls",
    [
        ({}, "generation_validation", 2),
        (InvalidModelResponseError("PRIVATE DECISION TEXT"), "provider_response", 2),
        (ProviderTimeoutError("PRIVATE DECISION TEXT", "timeout"), "provider_timeout", 1),
        (ProviderUnavailableError("PRIVATE DECISION TEXT"), "provider_unavailable", 1),
    ],
)
def test_failures_log_only_safe_categories_and_preserve_call_counts(caplog, failure, category, calls):
    caplog.set_level(logging.WARNING, logger="uvicorn.error")
    provider = RecordingProvider(failure)

    with pytest.raises((
        InvalidModelResponseError,
        StrategyGenerationError,
        ProviderTimeoutError,
        ProviderUnavailableError,
    )):
        StrategyOrchestrator(provider).generate(private_input())

    logs = messages(caplog)
    assert len(provider.calls) == calls
    assert any(f"category={category}" in line for line in logs)
    assert not any(marker in " ".join(logs) for marker in PRIVATE_MARKERS)


def test_structural_validation_failure_has_distinct_safe_category(caplog, monkeypatch):
    import app.strategy.orchestrator as module

    caplog.set_level(logging.WARNING, logger="uvicorn.error")
    provider = RecordingProvider(valid_model_output())

    def reject(*_):
        raise StrategyValidationError(["PRIVATE GENERATED APPROACH"])

    monkeypatch.setattr(module, "validate_strategy_result", reject)
    with pytest.raises(StrategyValidationError):
        StrategyOrchestrator(provider).generate(private_input())

    logs = messages(caplog)
    assert len(provider.calls) == 2
    assert any("category=structural_validation" in line for line in logs)
    assert not any(marker in " ".join(logs) for marker in PRIVATE_MARKERS)


def test_success_logs_attempt_without_false_terminal_failure(caplog):
    caplog.set_level(logging.WARNING, logger="uvicorn.error")
    provider = RecordingProvider(valid_model_output())

    StrategyOrchestrator(provider).generate(private_input())

    logs = messages(caplog)
    assert len(provider.calls) == 1
    assert any("strategy_generation_stage=attempt_succeeded attempt=1" in line for line in logs)
    assert not any("strategy_generation_stage=terminal_failure" in line for line in logs)
    assert not any(marker in " ".join(logs) for marker in PRIVATE_MARKERS)
