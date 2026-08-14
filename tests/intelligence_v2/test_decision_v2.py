from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, event, insert
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.business_profile_table import business_profile_table
from app.db.database import metadata
from app.db.organization_table import organization_table
from app.db.user_table import user_table
from app.db.workspace_member_table import workspace_member_table
from app.db.workspace_table import workspace_table
from app.db.memory_table import memory_table
from app.db.knowledge_table import knowledge_table
from app.intelligence_v2.classifier import decision_classifier
from app.intelligence_v2.context import ContextAccessError, EnterpriseContextAssembler
from app.intelligence_v2.contracts import AssumptionItem, AssumptionStatus, DecisionType, EvidenceItem, EvidenceSourceType, GapImportance
from app.intelligence_v2.service import decision_v2_service


DELIVERY_PROMPT = "Our delivery costs have been increasing and customers are complaining about late deliveries. I want to reduce delivery costs by 20% over the next 6 months without reducing service quality. What should we do?"


@pytest.fixture()
def session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    event.listen(engine, "connect", lambda connection, _: connection.execute("PRAGMA foreign_keys=ON"))
    metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    db = factory()
    db.execute(insert(user_table), [{"id": 1, "email": "owner@test", "password_hash": "x", "full_name": "Owner"}, {"id": 2, "email": "other@test", "password_hash": "x", "full_name": "Other"}])
    db.execute(insert(organization_table), {"id": 1, "name": "NorthStar", "slug": "northstar", "owner_user_id": 1, "industry": "Logistics", "company_size": "100-249", "account_type": "business"})
    db.execute(insert(organization_table), {"id": 2, "name": "Other", "slug": "other", "owner_user_id": 2, "industry": None, "company_size": None, "account_type": "business"})
    db.execute(insert(workspace_table), [{"id": 1, "organization_id": 1, "created_by_user_id": 1, "name": "Operations", "slug": "northstar-operations", "workspace_type": "operations"}, {"id": 2, "organization_id": 2, "created_by_user_id": 2, "name": "Other", "slug": "other-workspace", "workspace_type": "business"}])
    db.execute(insert(workspace_member_table), [{"workspace_id": 1, "user_id": 1, "role": "owner", "status": "active", "is_active": True}, {"workspace_id": 2, "user_id": 2, "role": "owner", "status": "active", "is_active": True}])
    db.execute(insert(business_profile_table).values(id=1, organization_id=1, workspace_id=1, business_name="NorthStar Logistics", legal_name=None, industry="Logistics", business_stage="growth", business_model="delivery_network", mission="Reliable delivery", vision=None, description=None, target_market="Regional retailers", target_customer="Retail operations", geographic_focus="Ontario", products_services="Delivery services", pricing_model="Per delivery", business_goals="Improve on-time delivery", current_challenges="Rising delivery cost", competitive_advantage="Regional coverage", is_active=True))
    db.commit()
    yield db
    db.close()


def test_delivery_case_is_cost_and_operations_not_market_expansion():
    result = decision_classifier.classify(DELIVERY_PROMPT)
    assert result.decision_type is DecisionType.COST_REDUCTION
    assert DecisionType.OPERATIONAL_OPTIMIZATION in result.secondary_types
    assert DecisionType.MARKET_EXPANSION not in [result.decision_type, *result.secondary_types]
    assert "cost_baseline" in result.required_data_domains


@pytest.mark.parametrize(("query", "expected"), [
    ("Should we raise our subscription pricing without increasing churn?", DecisionType.PRICING),
    ("Should we hire two dispatch coordinators for our growing team?", DecisionType.HIRING),
    ("Should we expand into the Quebec market next year?", DecisionType.MARKET_EXPANSION),
])
def test_taxonomy_classifies_distinct_decision_types(query, expected):
    assert decision_classifier.classify(query).decision_type is expected


def test_taxonomy_preserves_conflicting_secondary_types():
    result = decision_classifier.classify("Should we reduce delivery costs before expanding into a new market?")
    assert result.decision_type is DecisionType.COST_REDUCTION
    assert DecisionType.MARKET_EXPANSION in result.secondary_types
    assert result.rationale


def test_contracts_preserve_evidence_and_assumption_structure():
    evidence = EvidenceItem("profile:1", EvidenceSourceType.ORGANIZATION_PROFILE, "business_profiles", structured_value={"industry": "Logistics"}, timestamp=datetime.now(timezone.utc), provenance={"record_id": 1})
    assumption = AssumptionItem("Carrier capacity is stable", "user_statement", 0.4, AssumptionStatus.UNVERIFIED, "Routing actions may not be feasible")
    assert evidence.structured_value["industry"] == "Logistics"
    assert assumption.status is AssumptionStatus.UNVERIFIED


def test_context_assembler_uses_persisted_values_without_invention(session):
    context, evidence = EnterpriseContextAssembler().assemble(db=session, user_id=1, organization_id=1, workspace_id=1)
    assert context["organization"]["name"] == "NorthStar"
    assert context["business_profile"]["business_model"] == "delivery_network"
    assert context["business_profile"]["vision"] is None
    assert len(evidence) == 3


def test_context_assembler_is_tenant_safe(session):
    with pytest.raises(ContextAccessError):
        EnterpriseContextAssembler().assemble(db=session, user_id=1, organization_id=2, workspace_id=2)


def test_delivery_v2_detects_critical_operational_gaps_and_clarifies(session):
    state = decision_v2_service.analyze_request(db=session, user_id=1, organization_id=1, workspace_id=1, user_query=DELIVERY_PROMPT, session_id=7)
    assert state.request.target == "20%"
    assert state.request.timeframe == "6 months"
    assert state.request.constraints == ["Do not reduce service quality"]
    assert state.clarification.should_clarify is True
    assert 2 <= len(state.clarification.questions) <= 5
    assert {gap.field for gap in state.information_gaps} >= {"current_cost_baseline", "cost_breakdown", "service_level_baseline"}
    assert all(gap.importance in {GapImportance.CRITICAL, GapImportance.HIGH} for gap in state.information_gaps)
    assert state.recommendations == []
    assert state.selected_tools == []


def test_context_values_can_satisfy_specific_gap_signals(session):
    prompt = "Reduce delivery costs from $14.20 cost per delivery; fuel and carrier fees are the breakdown; 5000 deliveries per month; on-time SLA is 98%; we use a third-party carrier."
    state = decision_v2_service.analyze_request(db=session, user_id=1, organization_id=1, workspace_id=1, user_query=prompt)
    fields = {gap.field for gap in state.information_gaps}
    assert "current_cost_baseline" not in fields
    assert "cost_breakdown" not in fields
    assert "delivery_volume" not in fields
    assert "service_level_baseline" not in fields
    assert "process_or_carrier_model" not in fields


def _memory(session, **values):
    defaults = {"organization_id": 1, "workspace_id": 1, "user_id": None, "memory_type": "conversation", "content": "", "metadata": None}
    defaults.update(values)
    session.execute(insert(memory_table).values(**defaults))


def _knowledge(session, **values):
    defaults = {"organization_id": 1, "workspace_id": 1, "user_id": None, "fact_type": "operations", "fact_value": "", "source": "verified_import"}
    defaults.update(values)
    session.execute(insert(knowledge_table).values(**defaults))


def test_memory_evidence_preserves_numeric_percent_date_count_budget_and_duration(session):
    _memory(session, content="Delivery cost is $14.20 per order. On-time rate is 84%. Contract expires 2027-01-15. We operate 12 delivery vans. Budget is $250,000 for 18 months.")
    session.commit()
    state = decision_v2_service.analyze_request(db=session, user_id=1, organization_id=1, workspace_id=1, user_query="What delivery cost, service rate, vans, budget and contract date did I tell you?")
    memory = next(item for item in state.evidence if item.id.startswith("memory:"))
    assert "$14.20 per order" in memory.content
    assert "84%" in memory.content and "2027-01-15" in memory.content and "12 delivery vans" in memory.content
    assert "$250,000" in memory.content and "18 months" in memory.content
    assert memory.provenance["score"] > 0 and memory.provenance["why_matched"]


def test_memory_ranking_is_stable_recency_aware_and_never_uses_zero_vector(session):
    _memory(session, content="Marketing brand campaign notes")
    _memory(session, content="Delivery cost is $14.20 per order")
    session.commit()
    first = decision_v2_service.memory_retriever.retrieve(db=session, organization_id=1, workspace_id=1, user_id=1, query="delivery cost per order")
    second = decision_v2_service.memory_retriever.retrieve(db=session, organization_id=1, workspace_id=1, user_id=1, query="delivery cost per order")
    assert [item.id for item in first] == [item.id for item in second]
    assert first[0].content == "Delivery cost is $14.20 per order"
    assert "deterministic-token-hash-v1" in first[0].provenance["why_matched"][1]


def test_memory_scope_prevents_workspace_user_session_and_org_leakage(session):
    _memory(session, content="Organization global delivery cost $14.20 per order", workspace_id=None)
    _memory(session, content="Other organization secret $99 per order", organization_id=2, workspace_id=2)
    _memory(session, content="Other user private secret", user_id=2)
    _memory(session, content="Other session secret", metadata={"session_id": 99})
    session.commit()
    result = decision_v2_service.memory_retriever.retrieve(db=session, organization_id=1, workspace_id=1, user_id=1, session_id=7, query="delivery cost secret")
    contents = [item.content for item in result]
    assert "Organization global delivery cost $14.20 per order" in contents
    assert all("Other organization" not in content and "Other user" not in content and "Other session" not in content for content in contents)


def test_knowledge_adapter_is_relevant_scoped_and_converts_to_evidence(session):
    _knowledge(session, fact_type="delivery_cost", fact_value="$14.20 per order")
    _knowledge(session, fact_type="competitor_price", fact_value="$99", organization_id=2, workspace_id=2)
    _knowledge(session, fact_type="private_note", fact_value="not visible", user_id=2)
    session.commit()
    result = decision_v2_service.knowledge_adapter.retrieve(db=session, organization_id=1, workspace_id=1, user_id=1, query="delivery cost per order")
    assert result[0].source_type is EvidenceSourceType.KNOWLEDGE_DOCUMENT
    assert result[0].structured_value["fact_value"] == "$14.20 per order"
    assert all("$99" not in (item.content or "") and "not visible" not in (item.content or "") for item in result)


def test_evidence_deduplication_preserves_one_claim_and_conflicts_are_surfaced(session):
    _memory(session, content="Delivery cost is $14.20 per order")
    _knowledge(session, fact_type="delivery_cost", fact_value="$14.20 per order")
    _memory(session, content="Delivery cost is $16.10 per order")
    session.commit()
    state = decision_v2_service.analyze_request(db=session, user_id=1, organization_id=1, workspace_id=1, user_query="reduce delivery cost by 20%")
    same_claims = [item for item in state.evidence if item.content and "$14.20 per order" in item.content]
    assert len(same_claims) == 1
    assert state.evidence_conflicts
    assert {"14.20 per order", "16.10 per order"} <= set(state.evidence_conflicts[0].values)


def test_northstar_multifact_evidence_reduces_gaps_without_fabrication(session):
    _memory(session, content="Our current delivery cost is $14.20 per order.")
    _memory(session, content="Our on-time delivery rate is 84%.")
    _knowledge(session, fact_type="fleet_size", fact_value="We operate 12 delivery vans.")
    session.commit()
    state = decision_v2_service.analyze_request(db=session, user_id=1, organization_id=1, workspace_id=1, user_query="We need to reduce delivery costs by 20% within 6 months without reducing service quality.")
    evidence_text = " ".join(item.content or "" for item in state.evidence)
    assert "$14.20 per order" in evidence_text and "84%" in evidence_text and "12 delivery vans" in evidence_text
    assert state.classification.decision_type is DecisionType.COST_REDUCTION
    assert DecisionType.OPERATIONAL_OPTIMIZATION in state.classification.secondary_types
    assert state.request.quantitative_context["delivery_cost_target"] == "11.36"
    fields = {gap.field for gap in state.information_gaps}
    assert "current_cost_baseline" not in fields and "service_level_baseline" not in fields and "process_or_carrier_model" not in fields
    assert all(term not in evidence_text.lower() for term in ("fuel cost", "labor cost", "maintenance cost", "route count", "customer sla"))
