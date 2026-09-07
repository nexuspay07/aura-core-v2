from app.intelligence_v2.contracts import DecisionType
from app.intelligence_v2.fact_extraction import extract_fact_ledger, is_business_scenario
from app.intelligence_v2.model_provider import InvalidModelResponseError, MockModelProvider
from app.intelligence_v2.orchestrator import DecisionAnalysisOrchestrator, SYSTEM_PROMPT
from app.intelligence_v2.service import decision_v2_service
from tests.intelligence_v2.test_analysis_orchestrator import ready_personal_state, response
from tests.intelligence_v2.test_decision_v2 import session

SCENARIO_A="""I am a 24-year-old developer earning a $78k salary with $18k savings and $9k student debt at 6.5%. Living expenses are $2.4k monthly. My B2B startup has 14 paying customers, $2.1k MRR, 12% monthly growth, and the top 2 customers are 45% of revenue. I spend 20 hours per week on it and face burnout. My long-term goal is to grow the startup while preserving financial security. Options are quit, stay 6 months, or seek 3-day employment. Rent may rise, a customer may expand, and I may earn $1.5k monthly freelancing. What should I do?"""
SCENARIO_B="""Our 8-person software company has $65k cash, $24k monthly revenue, and $21k monthly expenses. Our largest customer is 35% of revenue and renews in 60 days while evaluating a competitor. We have technical debt, 2 recent outages, and a 6-week infrastructure repair. Five customers requested analytics; 2 may pay $500-$1k monthly. It takes 8 weeks to build. Hiring 2 engineers costs $9k monthly. Should we repair infrastructure, build analytics, or hire?"""

def test_founder_scenario_a_extracts_known_financial_goal_and_constraints(session):
    ledger=extract_fact_ledger(SCENARIO_A); kinds={f["type"] for f in ledger["facts"]}
    assert {"salary","savings","debt","mrr","growth_rate","customer_count","customer_concentration","workload"}<=kinds
    state=decision_v2_service.analyze_request(db=session,user_id=1,organization_id=1,workspace_id=1,user_query=SCENARIO_A,decision_scope="auto")
    assert state.request.objective and len(state.clarification.questions)<=1
    assert all("income" not in q.lower() and "long-term goal" not in q.lower() for q in state.clarification.questions)

def test_founder_scenario_b_is_business_and_extracts_operating_facts(session):
    ledger=extract_fact_ledger(SCENARIO_B);kinds={f["type"] for f in ledger["facts"]}
    assert is_business_scenario(SCENARIO_B,ledger)
    assert {"cash","revenue","expenses","customer_concentration","team_size","hiring_cost","renewal_deadline"}<=kinds
    state=decision_v2_service.analyze_request(db=session,user_id=1,organization_id=1,workspace_id=1,user_query=SCENARIO_B,decision_scope="auto")
    assert state.request.source_metadata["decision_scope"]=="business"
    assert state.classification.decision_type is not DecisionType.PERSONAL_FINANCE
    assert all("what income is available" not in q.lower() for q in state.clarification.questions)

class SequenceProvider:
    provider_name="mock";model_name="test";capabilities={"structured_output"}
    def __init__(self,items):self.items=list(items);self.calls=[]
    def generate_structured(self,**kwargs):
        self.calls.append(kwargs)
        item=self.items.pop(0)
        if isinstance(item,Exception):raise item
        return item,{"provider":"mock","model":"test","input_tokens":10,"output_tokens":20,"reasoning_tokens":5,"visible_output_tokens":15,"total_tokens":30,"latency_ms":1}

def test_incomplete_max_tokens_retries_once_with_reduced_payload(session):
    provider=SequenceProvider([InvalidModelResponseError("truncated","incomplete_max_tokens",{}),response()])
    result=DecisionAnalysisOrchestrator(provider).analyze(ready_personal_state(session))
    assert result.status=="READY" and result.usage["retry_count"]==1 and len(provider.calls)==2
    assert provider.calls[1]["reasoning_effort"]=="low" and provider.calls[1]["payload"]["context"]=={}

def test_two_retryable_failures_return_safe_partial_state(session):
    error=InvalidModelResponseError("truncated","incomplete_max_tokens",{})
    result=DecisionAnalysisOrchestrator(SequenceProvider([error,error])).analyze(ready_personal_state(session))
    assert result.status=="PARTIAL" and result.result is None and result.usage["retry_count"]==1

def test_active_prompts_use_aevric_brand():
    assert "You are Aevric AI" in SYSTEM_PROMPT and "You are Aura" not in SYSTEM_PROMPT
