"""Phase 6 regressions for Personal classification and clarification isolation."""

from app.intelligence_v2.contracts import DecisionType
from app.intelligence_v2.service import decision_v2_service
from tests.intelligence_v2.test_decision_v2 import session


CAR_PURCHASE = """I have $32,000 in savings and I'm thinking about buying a car for $18,000 in cash. I earn $4,200 per month and my regular monthly expenses are about $2,600. I want to keep at least $20,000 in emergency savings because financial security is important to me, but I also need a reliable car. Should I buy the $18,000 car now, choose a cheaper car, or wait and save more?"""
BUSINESS_WORDS = {"delivery", "order", "fleet", "carrier", "on-time", "service-level"}


def analyze(db, query):
    return decision_v2_service.analyze_request(db=db, user_id=1, organization_id=1, workspace_id=1, user_query=query, decision_scope="personal")


def questions(state):
    return " ".join(state.clarification.questions).lower()


def test_car_purchase_never_uses_business_delivery_clarification(session):
    state = analyze(session, CAR_PURCHASE)
    assert state.classification.decision_type is DecisionType.MAJOR_PURCHASE
    assert state.analysis_status == "READY_FOR_ANALYSIS"
    assert not BUSINESS_WORDS.intersection(questions(state).replace("third-party", "carrier").split())


def test_personal_domains_receive_only_relevant_questions(session):
    cases = [
        ("I hate my job lately.", DecisionType.CAREER_DECISION, {"work", "income", "location", "time"}),
        ("I'm thinking about going back to school.", DecisionType.EDUCATION_DECISION, {"education", "program", "tuition"}),
        ("Can I afford to pay down my debt faster?", DecisionType.PERSONAL_FINANCE, {"income", "expenses", "debts"}),
        ("Should I move to Toronto?", DecisionType.RELOCATION, {"move", "income", "housing"}),
        ("Should I start a personal project?", DecisionType.PERSONAL_PROJECT, {"project", "time", "money"}),
        ("I'm not sure what I should do next.", DecisionType.LIFE_PLANNING, {"choice", "situation"}),
    ]
    for query, expected_type, relevant in cases:
        state = analyze(session, query)
        asked = questions(state)
        assert state.classification.decision_type is expected_type
        assert relevant.intersection(set(asked.replace("?", "").replace(",", "").split()))
        assert not any(word in asked for word in BUSINESS_WORDS)


def test_personal_scope_does_not_weaken_business_classification(session):
    business = decision_v2_service.analyze_request(db=session, user_id=1, organization_id=1, workspace_id=1, user_query="Reduce delivery costs by 20%.")
    personal = analyze(session, "Can I reduce my monthly expenses?")
    assert business.classification.decision_type is DecisionType.COST_REDUCTION
    assert "delivery" in questions(business)
    assert personal.classification.decision_type is DecisionType.PERSONAL_FINANCE
    assert "delivery" not in questions(personal)


def test_fresh_personal_states_do_not_share_clarification(session):
    career = analyze(session, "I hate my job lately.")
    relocation = analyze(session, "Should I move to Toronto?")
    assert career.clarification_state is not relocation.clarification_state
    assert not set(career.clarification.questions).intersection(relocation.clarification.questions)
    assert "career" not in questions(relocation) and "work right now" not in questions(relocation)
