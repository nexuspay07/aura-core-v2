from app.unified_intelligence.contracts import Capability, ModelResult
from app.unified_intelligence.model_router import ModelRouter
from app.unified_intelligence.orchestrator import UnifiedAuraOrchestrator
from app.unified_intelligence.router import UnifiedCapabilityRouter
import pytest


class LanguageProvider:
    provider_name = "offline"
    model_name = "test"
    capabilities = {"natural_text_generation"}
    def __init__(self): self.calls = 0
    def generate(self, request):
        self.last_request = request
        self.calls += 1
        return ModelResult("Compound interest is interest earned on principal and prior interest.", {"provider": "offline", "model": "test", "input_tokens": 4, "output_tokens": 10})


def test_general_questions_are_not_decisions_and_use_model_capability():
    provider = LanguageProvider()
    aura = UnifiedAuraOrchestrator(models=ModelRouter(provider))
    route = aura.prepare("What is compound interest?")
    assert route.capabilities_required == (Capability.GENERAL,)
    assert not route.requires_decision_analysis
    assert aura.answer_non_decision("What is compound interest?", route)["mode"] == "GENERAL"
    assert provider.calls == 1


def test_current_request_fails_truthfully_without_model_call():
    provider = LanguageProvider()
    aura = UnifiedAuraOrchestrator(models=ModelRouter(provider))
    route = aura.prepare("What are today's biggest economic stories?")
    response = aura.answer_non_decision("What are today's biggest economic stories?", route)
    assert route.requires_current_information and Capability.CURRENT in route.capabilities_required
    assert response["mode"] == "CURRENT_INFORMATION_UNAVAILABLE"
    assert "live retrieval isn't connected" in response["message"]
    assert provider.calls == 0


def test_personal_decision_and_hybrid_routes_are_additive():
    router = UnifiedCapabilityRouter()
    decision = router.route("Should I buy this car given my savings?")
    assert {Capability.PERSONAL, Capability.DECISION} <= set(decision.capabilities_required)
    hybrid = router.route("What happened with rates today and should I change my home plan?")
    assert {Capability.CURRENT, Capability.PERSONAL, Capability.DECISION} <= set(hybrid.capabilities_required)


def test_social_turn_is_deterministic_and_skips_model():
    provider = LanguageProvider()
    aura = UnifiedAuraOrchestrator(models=ModelRouter(provider))
    route = aura.prepare("Hello")
    assert not route.requires_language_model
    assert aura.answer_non_decision("Hello", route)["mode"] == "CONVERSATION"
    assert provider.calls == 0


def test_general_follow_up_uses_only_bounded_safe_conversation_context():
    provider = LanguageProvider(); aura = UnifiedAuraOrchestrator(models=ModelRouter(provider))
    turns = [{"role": "user" if index % 2 == 0 else "assistant", "content": f"turn-{index} " + ("x" * 1200), "payload": {"private": "not serialized"}} for index in range(10)]
    route = aura.prepare("Give me an example with $5,000.")
    aura.answer_non_decision("Give me an example with $5,000.", route, turns=turns)
    assert "turn-0" not in provider.last_request.prompt and "turn-9" in provider.last_request.prompt
    assert "private" not in provider.last_request.prompt
    assert provider.last_request.context["conversation_turn_count"] <= 6
    assert len(provider.last_request.prompt) < 7000


def test_document_evidence_uses_same_general_turn_with_citation_label():
    from types import SimpleNamespace
    provider = LanguageProvider(); aura = UnifiedAuraOrchestrator(models=ModelRouter(provider))
    route = aura.prepare("Summarize this uploaded document.")
    evidence = [SimpleNamespace(citation_label="Offer, section 2", content="The role has a six-month probation period.")]
    response = aura.answer_non_decision("Summarize this uploaded document.", route, document_evidence=evidence)
    assert response["mode"] == "GENERAL"
    assert "[Offer, section 2]" in provider.last_request.prompt
    assert provider.last_request.context["document_evidence_count"] == 1


@pytest.mark.parametrize("question", [
    "What's happening in the world today?",
    "What's the latest political news?",
    "How did markets perform today?",
])
def test_alpha_current_questions_make_no_model_call_or_fresh_claim(question):
    provider = LanguageProvider(); aura = UnifiedAuraOrchestrator(models=ModelRouter(provider))
    response = aura.answer_non_decision(question, aura.prepare(question))
    assert response["mode"] == "CURRENT_INFORMATION_UNAVAILABLE"
    assert "can't verify current information" in response["message"]
    assert "http" not in response["message"] and provider.calls == 0


@pytest.mark.parametrize("question", [
    "Explain photosynthesis simply.", "Teach me how recursion works.",
    "Help me write a polite follow-up email.", "Brainstorm names for a bakery.",
    "Explain this Python TypeError.", "Plan a three-day study schedule.",
    "Compare leasing and buying a car in general.",
])
def test_representative_general_requests_remain_general(question):
    route = UnifiedCapabilityRouter().route(question)
    assert route.primary_intent == "general"
    assert Capability.DECISION not in route.capabilities_required


@pytest.mark.parametrize("question", [
    "Help me choose between college and working full-time.",
    "What would you do between these two options?",
    "I'm torn between renting and buying.",
    "Is starting this company right now sensible for me?",
    "I don't know whether I should move or stay.",
])
def test_natural_personal_choice_language_routes_to_decision(question):
    route = UnifiedCapabilityRouter().route(question)
    assert route.primary_intent == "decision"
    assert {Capability.PERSONAL, Capability.DECISION} <= set(route.capabilities_required)


@pytest.mark.parametrize("question", [
    "Explain the difference between renting and buying.",
    "What is a mortgage?",
    "Write an email to my landlord.",
    "Give me five business ideas.",
    "Summarize this paragraph.",
])
def test_information_and_creation_controls_remain_general(question):
    route = UnifiedCapabilityRouter().route(question)
    assert route.primary_intent == "general"
    assert Capability.DECISION not in route.capabilities_required


def test_explicit_constraint_correction_continues_only_an_existing_decision():
    router = UnifiedCapabilityRouter()
    prior = ["I want to start a cleaning company and I have $3,000."]
    assert router.route("Actually I only have $500.", prior_user_turns=prior).requires_decision_analysis
    assert not router.route("Actually, explain that more simply.").requires_decision_analysis
