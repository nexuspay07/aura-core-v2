from app.db.memory_table import memory_table
from app.intelligence_v2.clarification import information_sufficiency_service, structured_answer_extractor
from app.intelligence_v2.contracts import DecisionRequest, EvidenceConflict, GapImportance, InformationGap, SufficiencyStatus
from app.intelligence_v2.service import decision_v2_service
from tests.intelligence_v2.test_decision_v2 import session

def _gap(field, importance=GapImportance.CRITICAL):
    return InformationGap(field,"needed",importance,"changes decision",False,f"What is {field}?")

def test_value_of_information_prioritizes_blocking_critical_gaps():
    ranked=information_sufficiency_service.prioritize([_gap("optional",GapImportance.LOW),_gap("baseline")])
    assert [item.gap.field for item in ranked]==["baseline","optional"] and ranked[0].score>ranked[1].score

def test_conflict_becomes_one_specific_clarification_not_silent_choice(session):
    session.execute(memory_table.insert(),[{"organization_id":1,"workspace_id":1,"content":"Delivery cost is $14.20 per order"},{"organization_id":1,"workspace_id":1,"content":"Delivery cost is $15.10 per order"}]);session.commit()
    state=decision_v2_service.analyze_request(db=session,user_id=1,organization_id=1,workspace_id=1,user_query="reduce delivery costs by 20%")
    assert state.sufficiency.status is SufficiencyStatus.CONTRADICTORY
    assert len(state.clarification.questions)<=5 and "conflicting values" in state.clarification.questions[0]

def test_answer_extraction_promotes_session_evidence_without_memory_write(session):
    request=DecisionRequest(1,1,1,"reduce delivery cost",missing_information=[_gap("current_cost_baseline")])
    item=structured_answer_extractor.extract(question="What is current_cost_baseline?",answer="$14.20 per order.",request=request,turn=1)
    assert item.structured_value=={"topic":"current_cost_baseline","value":"14.20","unit":"USD/order","confirmed":True}
    assert item.provenance["memory_promotion"]=="candidate" and item.permission_scope=="session"

def test_uncertain_answer_is_preserved_but_not_overinterpreted(session):
    state=decision_v2_service.analyze_request(db=session,user_id=1,organization_id=1,workspace_id=1,user_query="reduce delivery costs by 20%")
    question=state.clarification.questions[0]; state=decision_v2_service.apply_clarification_answer(state=state,question=question,answer="It varies a lot depending on the day")
    item=state.clarification_state.facts_added[-1]
    assert item.content.startswith("It varies") and item.structured_value["confirmed"] is False
    assert question in state.clarification_state.questions_answered and question not in state.clarification_state.unresolved_questions

def test_northstar_evidence_avoids_repeating_known_baseline_and_sla(session):
    session.execute(memory_table.insert(),[{"organization_id":1,"workspace_id":1,"content":"Delivery cost is $14.20 per order. On-time delivery rate is 84%. We operate 12 vans. Fuel 28%, maintenance 16%, driver labor 34%."}]);session.commit()
    state=decision_v2_service.analyze_request(db=session,user_id=1,organization_id=1,workspace_id=1,user_query="reduce delivery costs by 20% within 6 months without reducing service quality")
    asked=" ".join(state.clarification.questions).lower()
    assert "current average delivery cost" not in asked and "on-time delivery rate" not in asked
    assert state.analysis_status=="CLARIFICATION_REQUIRED"

def test_no_evidence_northstar_requires_small_high_value_round_and_proceed_is_explicit(session):
    state=decision_v2_service.analyze_request(db=session,user_id=1,organization_id=1,workspace_id=1,user_query="reduce delivery costs by 20% within 6 months without reducing service quality")
    assert state.sufficiency.status is SufficiencyStatus.INSUFFICIENT and 1<=len(state.clarification.questions)<=5
    state=decision_v2_service.proceed_with_assumptions(state)
    assert state.analysis_status=="READY_FOR_ANALYSIS" and state.proceed_decision.allowed and state.assumptions

def test_personal_career_and_sufficient_offer_comparison_do_not_force_business_gaps(session):
    career=decision_v2_service.analyze_request(db=session,user_id=1,organization_id=1,workspace_id=1,user_query="I'm deciding whether to leave my current job and return to school for a two-year program.",decision_scope="personal")
    assert career.analysis_status=="CLARIFICATION_REQUIRED" and any("career outcome" in q.lower() for q in career.clarification.questions)
    offers=decision_v2_service.analyze_request(db=session,user_id=1,organization_id=1,workspace_id=1,user_query="I have two job offers. Offer A pays $70,000, is fully remote, and has limited promotion opportunities. Offer B pays $78,000, requires a 60-minute commute each way, and has a clear management track. My top priority is career growth, but I strongly value having evenings free.",decision_scope="personal")
    assert offers.analysis_status=="READY_FOR_ANALYSIS" and not offers.clarification.questions
