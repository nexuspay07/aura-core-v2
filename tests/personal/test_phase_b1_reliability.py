from app.intelligence_v2.classifier import classify_personal
from app.intelligence_v2.clarification import personal_gaps
from app.intelligence_v2.contracts import DecisionType
from app.intelligence_v2.service import authoritative_user_context
from app.unified_intelligence.router import UnifiedCapabilityRouter


def _user_turn(content: str) -> dict[str, str]:
    return {"role": "user", "content": content}


def test_actionable_cleaning_business_decision_does_not_block_on_unknown_focus():
    query = "Is starting a weekend cleaning business sensible for me? I can invest $700 and six hours a week."
    classification = classify_personal(query)

    assert UnifiedCapabilityRouter().route(query).requires_decision_analysis
    assert classification.decision_type is DecisionType.PERSONAL_PROJECT
    assert personal_gaps(query, classification.decision_type) == []


def test_course_choice_is_education_not_generic_finance():
    query = "Help me choose a course. My budget is $2,000 and I only have six months."
    classification = classify_personal(query)

    assert classification.decision_type is DecisionType.EDUCATION_DECISION
    assert not any(gap.field in {"income", "obligations"} for gap in personal_gaps(query, classification.decision_type))


def test_new_budget_overrides_old_budget_without_losing_goal():
    context, prior, authoritative = authoritative_user_context(
        "Actually I only have $500. Revise what I should do next.",
        [_user_turn("I want to start a cleaning company and my budget is $2,000.")],
    )

    assert "$2,000" not in context
    assert "$500" in context
    assert "cleaning company" in context
    assert authoritative["budget"] == "I only have $500"
    assert prior[0]["superseded_slots"] == ["budget"]


def test_new_deadline_overrides_old_deadline():
    context, _, authoritative = authoritative_user_context(
        "I need to do it within 30 days instead.",
        [_user_turn("I want to launch in 90 days with a small budget.")],
    )

    assert "90 days" not in context
    assert "30 days" in context
    assert authoritative["deadline"] == "within 30 days"


def test_explicit_deadline_correction_overrides_old_fact():
    context, _, authoritative = authoritative_user_context(
        "Correction: it is actually 45 days. What should I do first?",
        [_user_turn("My deadline is 60 days.")],
    )

    assert "60 days" not in context
    assert "45 days" in context
    assert "45 days" in authoritative["deadline"]


def test_assistant_fact_is_not_promoted_or_allowed_to_override_user_fact():
    context, prior, authoritative = authoritative_user_context(
        "Use the budget I gave you earlier.",
        [
            _user_turn("My budget is $2,000."),
            {"role": "assistant", "content": "Let's assume your budget is $9,000."},
        ],
    )

    assert "$2,000" in context
    assert "$9,000" not in context
    assert authoritative["budget"] == "My budget is $2,000"
    assert len(prior) == 1


def test_personal_planning_horizon_does_not_route_to_current_information():
    router = UnifiedCapabilityRouter()

    route = router.route("Help me prioritize launching, interviews, bookkeeping, and branding this week.")
    current = router.route("What are the most important AI product announcements this week?")

    assert not route.requires_current_information
    assert current.requires_current_information


def test_conflicting_career_constraints_can_reach_bounded_analysis():
    query = "I want to quit my job, keep the same income, work half as much, and take no financial risk. What should I do?"
    classification = classify_personal(query)

    assert classification.decision_type is DecisionType.CAREER_DECISION
    assert personal_gaps(query, classification.decision_type) == []


def test_truly_underspecified_decision_still_requires_clarification():
    query = "I may leave my current job."
    classification = classify_personal(query)
    fields = {gap.field for gap in personal_gaps(query, classification.decision_type)}

    assert classification.decision_type is DecisionType.CAREER_DECISION
    assert {"career_objective", "career_constraints"} <= fields

