import logging

import pytest

from app.intelligence_v2.fact_extraction import extract_fact_ledger
from app.intelligence_v2.service import decision_v2_service
from app.unified_intelligence.router import UnifiedCapabilityRouter
from tests.intelligence_v2.test_decision_v2 import session


EDUCATION = """I'm currently studying Information Technology. My three options are:
1. Enter the workforce after this program.
2. Continue into another degree.
3. Build practical projects while testing a business.
My goals, financial constraints, and preferences are provided. Compare these options and provide a recommendation, trade-offs, risks, uncertainty, what could change the recommendation, and a 12-month plan."""


@pytest.mark.parametrize("message", [
    EDUCATION,
    "I currently earn $78,000. My options are stay in my role, accept the supplied offer, or change fields. Compare these options and provide a recommendation based on my commute, goals, and constraints.",
    "We currently have 20 customers. Our options are hire now, wait six months, or use contractors. Compare these options and risks using the information provided.",
    "My current role has the constraints described here. My options are stay, accept the other role, or retrain. Provide a recommendation.",
    "My three options are: 1. stay. 2. move. 3. retrain. Recommend a path.",
    "Our options are hire, automate, or wait. Analyze the trade-offs and risks.",
])
def test_self_contained_temporal_decisions_do_not_require_retrieval(message):
    route = UnifiedCapabilityRouter().route(message)
    assert route.requires_decision_analysis
    assert not route.requires_current_information
    assert route.routing_event == "route_decision_self_contained"
    if "current" in message.lower():
        assert route.freshness_source == "user_context"


def test_production_shaped_education_preserves_three_options():
    route = UnifiedCapabilityRouter().route(EDUCATION)
    ledger = extract_fact_ledger(EDUCATION)
    assert route.requires_decision_analysis and not route.requires_current_information
    assert len(ledger["options"]) == 3


@pytest.mark.parametrize("message", [
    "Which university currently has the lowest tuition?",
    "What is the current average software salary in Toronto?",
    "What current law or regulation applies to this arrangement?",
    "What are the latest market developments today?",
    "What are X's current admission requirements?",
    "What is the current market size?",
])
def test_external_current_fact_requests_require_current_intelligence(message):
    route = UnifiedCapabilityRouter().route(message)
    assert route.requires_current_information
    assert not route.requires_decision_analysis
    assert route.freshness_source == "external_dependency"


@pytest.mark.parametrize("user_fact, external_request", [
    ("My current salary is $78,000.", "What is the current market salary?"),
    ("I'm currently enrolled at X.", "What are X's current admission requirements?"),
    ("My business currently has 20 customers.", "What is the current market size?"),
])
def test_user_current_context_contrasts_with_external_dependency(user_fact, external_request):
    router = UnifiedCapabilityRouter()
    supplied = router.route(user_fact)
    external = router.route(external_request)
    assert not supplied.requires_current_information
    assert supplied.freshness_source == "user_context"
    assert external.requires_current_information
    assert external.freshness_source == "external_dependency"


@pytest.mark.parametrize("message", [
    "Compare these two job offers using the salary and commute I provided, and tell me whether each salary is competitive in Toronto right now.",
    "My options are attend X, attend Y, or work. Compare these options using my goals and also tell me the current tuition.",
    "Our options are hire, automate, or wait. Compare these options using our supplied metrics under current regulations.",
])
def test_hybrid_decisions_preserve_decision_analysis_and_external_dependency(message):
    route = UnifiedCapabilityRouter().route(message)
    assert route.requires_decision_analysis and route.requires_current_information
    assert route.routing_event == "route_decision_hybrid"
    assert route.freshness_source == "external_dependency"


def test_freshness_dependent_decision_without_supplied_context_uses_current_boundary():
    route = UnifiedCapabilityRouter().route("Which option is better under current Canadian tax law?")
    assert route.requires_current_information and not route.requires_decision_analysis
    assert route.routing_event == "route_decision_freshness_dependent"


def test_hybrid_unavailable_factor_is_explicit_and_nonblocking(session):
    message = "My options are attend X, attend Y, or work. Compare these options using my goals and also tell me the current tuition."
    state = decision_v2_service.analyze_request(
        db=session, user_id=1, organization_id=1, workspace_id=1,
        user_query=message, decision_scope="auto", unresolved_current_information=True,
    )
    external = [gap for gap in state.information_gaps if gap.field == "current_external_fact"]
    assert len(external) == 1 and external[0].can_proceed_without
    assert state.request.source_metadata["freshness_dependency"] == "external_dependency"
    assert not any(gap.field == "current_external_fact" for gap in (state.clarification.blocking_gaps if state.clarification else []))


def test_routing_observability_is_enum_only(caplog):
    secret = "private-salary-78413"
    route = UnifiedCapabilityRouter().route(f"My current salary is ${secret}. My options are stay, move, or retrain. Provide a recommendation.")
    with caplog.at_level(logging.INFO):
        logging.getLogger("routing-test").info("routing_event=%s freshness_source=%s", route.routing_event, route.freshness_source or "none")
    assert route.routing_event in caplog.text and "freshness_source=user_context" in caplog.text
    assert secret not in caplog.text
