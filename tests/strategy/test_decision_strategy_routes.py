import logging

import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, insert, select, update
from sqlalchemy.orm import sessionmaker
from app.db.database import metadata
from app.db.user_table import user_table
from app.db.organization_table import organization_table
from app.db.workspace_table import workspace_table
from app.db.intelligence_session_table import intelligence_session_table
from app.db.decision_execution_snapshot_table import decision_execution_snapshot_table
from app.db.personal_decision_table import personal_decision_table
from app.db.strategy_resource_table import strategy_resource_table, strategy_revision_table
from app.db.strategy_idempotency_table import strategy_create_idempotency_table
from app.api import personal_decision_routes
from app.strategy import resource_routes, routes
from app.strategy.application import StrategyApplicationService, StrategyApplicationValidationError
from app.strategy.contracts import StrategyPhase, StrategyResult, SuccessMeasure
from app.strategy.idempotency import StrategyCreateIdempotencyRepository
from app.strategy.idempotency import StrategyCreateOperation, strategy_create_from_decision_fingerprint
from app.strategy.persistence import StrategyRepository
from app.strategy.adapters import build_strategy_input_from_snapshot
from app.strategy.contracts import StrategyScope
from app.strategy.orchestrator import StrategyGenerationError
from app.strategy.quality import StrategyQualityError, StrategyQualityIssue
from app.strategy.validation import StrategyValidationError
from app.personal.decisions import personal_decision_service

def canonical(selected="Offer A"):
    return {"decision_type":"career_decision","objective":"Choose a role","selected_option":selected,"constraints":["Protect evenings"],"resources":[{"type":"time","value":"Evenings"}],"evidence_references":[{"evidence_id":"user-query","citation_label":"User statement"}],"assumptions":[{"statement":"Both offers remain open","source":"user"}],"alternatives":[{"option":"Offer A","benefits":[],"downsides":[],"evidence_ids":[],"assumptions":[],"conditions_for_success":[]}],"risks":["Growth may stall"],"uncertainties":["Promotion timing"],"time_horizon":"one year","change_conditions":["Offer B confirms promotion"],"confidence":"MODERATE","confidence_rationale":["Some uncertainty remains"],"schema_version":1}

def laptop_canonical():
    return {
        "decision_type":"major_purchase",
        "objective":"PRIVATE LAPTOP DECISION",
        "selected_option":"PRIVATE PRESERVE SAVINGS RECOMMENDATION",
        "constraints":["PRIVATE $1,500 PURCHASE CONSTRAINT"],
        "resources":[{"type":"savings","value":"PRIVATE $5,000 SAVINGS"}],
        "evidence_references":[],
        "assumptions":[{"statement":"PRIVATE CURRENT LAPTOP ASSUMPTION","source":"user"}],
        "alternatives":[{"option":"PRIVATE BUY OPTION","benefits":[],"downsides":[],"evidence_ids":[],"assumptions":[],"conditions_for_success":[]}],
        "risks":["PRIVATE LAPTOP FAILURE RISK"],
        "uncertainties":["PRIVATE INCOME IMPORTANCE UNCERTAINTY"],
        "time_horizon":None,
        "change_conditions":["PRIVATE WORK CRITICAL CHANGE CONDITION"],
        "confidence":"MODERATE",
        "confidence_rationale":["PRIVATE CONFIDENCE RATIONALE"],
        "schema_version":1,
    }

class Capability:
    def __init__(self): self.calls=0; self.inputs=[]
    def generate(self, source, *, before_provider_attempt=None):
        self.calls+=1; self.inputs.append(source)
        if before_provider_attempt: before_provider_attempt()
        return StrategyResult(scope=source.scope,objective=source.objective,chosen_direction=source.chosen_direction,approach="Validate then commit.",phases=(StrategyPhase(1,"Validate","Reduce uncertainty."),),success_measures=(SuccessMeasure("Decision remains sound."),),change_conditions=source.change_conditions,confidence=source.confidence,confidence_rationale=source.confidence_rationale,source_decision_id=source.source_decision_id,source_reference=source.source_reference,constraints=source.constraints,assumptions=source.assumptions,resources=source.resources,risks=source.risks,alternatives=source.considered_alternatives,uncertainties=source.uncertainties,evidence_refs=source.evidence_refs,time_horizon=source.time_horizon)

@pytest.fixture
def api(tmp_path,monkeypatch):
    engine=create_engine(f"sqlite:///{tmp_path/'decision-strategy.db'}"); event.listen(engine,"connect",lambda c,_:c.execute("PRAGMA foreign_keys=ON")); metadata.create_all(engine); factory=sessionmaker(bind=engine); db=factory()
    db.execute(insert(user_table), [{"id":1,"email":"one@decision.test","password_hash":"x"},{"id":2,"email":"two@decision.test","password_hash":"x"}])
    db.execute(insert(organization_table), [{"id":10,"name":"One","slug":"one-decision","owner_user_id":1,"account_type":"business","plan":"free","subscription_status":"inactive","is_active":True},{"id":20,"name":"Two","slug":"two-decision","owner_user_id":2,"account_type":"business","plan":"free","subscription_status":"inactive","is_active":True}])
    db.execute(insert(workspace_table), [{"id":11,"organization_id":10,"created_by_user_id":1,"name":"One","slug":"one-decision","workspace_type":"business","is_active":True},{"id":12,"organization_id":10,"created_by_user_id":1,"name":"Other","slug":"other-decision","workspace_type":"business","is_active":True},{"id":21,"organization_id":20,"created_by_user_id":2,"name":"Two","slug":"two-decision","workspace_type":"business","is_active":True}])
    db.execute(insert(intelligence_session_table), {"id":50,"organization_id":10,"workspace_id":11,"created_by_user_id":1,"title":"Choice","goal":"Choose","session_type":"personal_ask_v2","status":"completed","is_active":True})
    db.execute(insert(decision_execution_snapshot_table), [{"id":101,"public_id":"00000000-0000-4000-8000-000000000101","intelligence_session_id":50,"user_id":1,"organization_id":10,"workspace_id":11,"snapshot_version":1,"snapshot_schema_version":1,"canonical_decision_json":canonical()},{"id":102,"public_id":"00000000-0000-4000-8000-000000000102","intelligence_session_id":50,"user_id":1,"organization_id":10,"workspace_id":11,"snapshot_version":2,"snapshot_schema_version":1,"canonical_decision_json":canonical("Offer B")}])
    db.execute(insert(personal_decision_table), [{"id":41,"public_id":"10000000-0000-4000-8000-000000000041","user_id":1,"organization_id":10,"workspace_id":11,"source_session_id":50,"canonical_snapshot_id":101,"title":"Choice","original_question":"Choose","decision_type":"career_decision","analysis_snapshot_json":{},"recommendation":"Offer A"},{"id":42,"public_id":"10000000-0000-4000-8000-000000000042","user_id":1,"organization_id":10,"workspace_id":12,"source_session_id":None,"canonical_snapshot_id":None,"title":"Historic","original_question":"Choose","decision_type":"general","analysis_snapshot_json":{},"recommendation":"Wait"}]); db.commit(); db.close()
    identity={"value":{"user":{"id":1},"organization":{"id":10},"workspace":{"id":11},"capabilities":["decisions"]}}
    async def current(_): return identity["value"]
    capability=Capability(); service=StrategyApplicationService(capability,StrategyRepository(),StrategyCreateIdempotencyRepository())
    monkeypatch.setattr(personal_decision_routes,"get_current_user_from_token",current); monkeypatch.setattr(personal_decision_routes,"SessionLocal",factory); monkeypatch.setattr(personal_decision_routes,"strategy_application_service",service)
    monkeypatch.setattr(routes,"get_current_user_from_token",current); monkeypatch.setattr(resource_routes,"SessionLocal",factory); monkeypatch.setattr(resource_routes,"strategy_application_service",service)
    app=FastAPI(); app.include_router(personal_decision_routes.router); app.include_router(resource_routes.router); app.add_exception_handler(RequestValidationError, personal_decision_routes.strategy_request_validation_handler)
    yield TestClient(app,raise_server_exceptions=False),factory,capability,identity
    engine.dispose()

HEADERS={"Authorization":"Bearer token","Idempotency-Key":"decision-key"}

def test_create_uses_exact_snapshot_persists_both_provenance_and_replays(api):
    client,factory,capability,_=api
    first=client.post("/personal/decisions/10000000-0000-4000-8000-000000000041/strategy",headers=HEADERS,json={"title":"Career strategy"})
    replay=client.post("/personal/decisions/10000000-0000-4000-8000-000000000041/strategy",headers=HEADERS,json={"title":"Career strategy"})
    assert first.status_code==201 and replay.status_code==201 and replay.json()["public_id"]==first.json()["public_id"] and capability.calls==1
    source=capability.inputs[0]; assert source.chosen_direction=="Offer A" and source.objective=="Choose a role" and source.scope.organization_id==10
    db=factory(); revision=db.execute(select(strategy_revision_table)).mappings().one(); assert revision["origin_type"]=="decision_derived" and revision["source_decision_id"]==41 and revision["source_decision_snapshot_id"]==101
    assert db.execute(select(strategy_create_idempotency_table.c.operation)).scalar_one()=="strategy_create_from_decision"; db.close()
    rendered=first.text; assert 'source_decision_id' not in rendered and 'source_decision_snapshot_id' not in rendered and 'canonical_decision_json' not in rendered


def test_personal_account_decision_strategy_returned_public_id_is_immediately_retrievable(api):
    client,factory,capability,identity=api
    db=factory(); db.execute(update(organization_table).where(organization_table.c.id.in_([10,20])).values(account_type="personal")); db.commit(); db.close()
    identity["value"]["organization"]["account_type"]="personal"

    created=client.post(
        "/personal/decisions/10000000-0000-4000-8000-000000000041/strategy",
        headers=HEADERS,json={"title":"Career strategy"},
    )
    assert created.status_code==201
    public_id=created.json()["public_id"]

    fetched=client.get(f"/strategy-resources/{public_id}",headers={"Authorization":"Bearer token"})
    listed=client.get("/strategy-resources",headers={"Authorization":"Bearer token"})
    assert fetched.status_code==200 and fetched.json()["public_id"]==public_id
    assert [item["public_id"] for item in listed.json()["items"]]==[public_id]
    db=factory(); resource=db.execute(select(strategy_resource_table)).mappings().one(); revision=db.execute(select(strategy_revision_table)).mappings().one(); db.close()
    assert resource["public_id"]==public_id and resource["owner_user_id"]==1
    assert resource["organization_id"] is None and resource["workspace_id"] is None
    assert revision["source_decision_id"]==41 and revision["source_decision_snapshot_id"]==101

    identity["value"]={"user":{"id":2},"organization":{"id":20,"account_type":"personal"},"workspace":{"id":21},"capabilities":["decisions"]}
    assert client.get(f"/strategy-resources/{public_id}",headers={"Authorization":"Bearer token"}).status_code==404
    assert capability.calls==1

def test_eligibility_choice_scope_and_request_fail_before_provider(api):
    client,factory,capability,identity=api
    assert client.post("/personal/decisions/41/strategy",headers=HEADERS,json={"title":"Plan"}).status_code==404
    assert client.post("/personal/decisions/10000000-0000-4000-8000-000000000041/strategy",headers=HEADERS,json={"title":"Plan","objective":"override"}).status_code==422
    identity["value"]={"user":{"id":2},"organization":{"id":20},"workspace":{"id":21},"capabilities":["decisions"]}
    assert client.post("/personal/decisions/10000000-0000-4000-8000-000000000041/strategy",headers=HEADERS,json={"title":"Plan"}).status_code==404
    identity["value"]={"user":{"id":1},"organization":{"id":10},"workspace":{"id":11},"capabilities":["decisions"]}
    db=factory(); db.execute(update(personal_decision_table).where(personal_decision_table.c.id==41).values(user_choice="Offer B")); db.commit(); db.close()
    mismatch=client.post("/personal/decisions/10000000-0000-4000-8000-000000000041/strategy",headers=HEADERS,json={"title":"Plan"})
    assert mismatch.status_code==409 and mismatch.json()["detail"]["code"]=="decision_choice_requires_reevaluation" and capability.calls==0

def test_historical_missing_header_conflict_and_in_progress(api):
    client,factory,capability,identity=api
    identity["value"]["workspace"]={"id":12}
    unavailable=client.post("/personal/decisions/10000000-0000-4000-8000-000000000042/strategy",headers=HEADERS,json={"title":"Plan"})
    assert unavailable.status_code==409 and unavailable.json()["detail"]["code"]=="decision_canonical_snapshot_unavailable"
    identity["value"]["workspace"]={"id":11}
    assert client.post("/personal/decisions/10000000-0000-4000-8000-000000000041/strategy",headers={"Authorization":"Bearer token"},json={"title":"Plan"}).status_code==422
    first=client.post("/personal/decisions/10000000-0000-4000-8000-000000000041/strategy",headers=HEADERS,json={"title":"Plan"}); assert first.status_code==201
    conflict=client.post("/personal/decisions/10000000-0000-4000-8000-000000000041/strategy",headers=HEADERS,json={"title":"Changed"}); assert conflict.status_code==409 and capability.calls==1
    db=factory(); decision,snapshot=personal_decision_service.strategy_source(db,public_id="10000000-0000-4000-8000-000000000041",user_id=1,organization_id=10,workspace_id=11); source=build_strategy_input_from_snapshot(snapshot.snapshot,scope=StrategyScope(1,10,11),source_decision_id=41,source_reference=f"personal-decision:{decision['public_id']}"); fingerprint=strategy_create_from_decision_fingerprint(title="Active",strategy_input=source,personal_decision_public_id=decision["public_id"],snapshot_public_id=snapshot.public_id,snapshot_version=snapshot.snapshot_version); StrategyCreateIdempotencyRepository().claim(db,idempotency_key="active-key",request_fingerprint=fingerprint,actor_user_id=1,scope=source.scope,operation=StrategyCreateOperation.FROM_DECISION); db.commit(); db.close()
    active=client.post("/personal/decisions/10000000-0000-4000-8000-000000000041/strategy",headers={**HEADERS,"Idempotency-Key":"active-key"},json={"title":"Active"}); assert active.status_code==409 and active.json()["detail"]["code"]=="strategy_creation_in_progress" and capability.calls==1


def strategy_http_logs(caplog):
    return [record.message for record in caplog.records if "strategy_http_stage=" in record.message]


def test_representative_laptop_path_logs_boundaries_without_private_content(api, caplog):
    client,factory,capability,_=api
    db=factory(); db.execute(update(decision_execution_snapshot_table).where(
        decision_execution_snapshot_table.c.id==101
    ).values(canonical_decision_json=laptop_canonical())); db.commit(); db.close()
    caplog.set_level(logging.WARNING,logger="uvicorn.error")

    response=client.post(
        "/personal/decisions/10000000-0000-4000-8000-000000000041/strategy",
        headers=HEADERS,json={"title":"PRIVATE STRATEGY TITLE"},
    )

    logs=strategy_http_logs(caplog); rendered=" ".join(logs)
    assert response.status_code==201 and capability.calls==1
    for stage in ("request_entered","decision_resolved","snapshot_resolved","adapter_completed","input_validation_completed","generation_entered","orchestrator_entered","persistence_entered","request_succeeded"):
        assert any(f"strategy_http_stage={stage}" in line for line in logs)
    for private in ("PRIVATE", "1,500", "5,000", "10000000-0000-4000-8000-000000000041", "decision-key"):
        assert private not in rendered


def test_fastapi_request_validation_is_distinct_and_response_is_unchanged(api, caplog):
    client,_,_,_=api
    caplog.set_level(logging.WARNING,logger="uvicorn.error")

    response=client.post(
        "/personal/decisions/10000000-0000-4000-8000-000000000041/strategy",
        headers={"Authorization":"Bearer token"},json={"title":"Plan"},
    )

    assert response.status_code==422 and isinstance(response.json()["detail"],list)
    assert any("category=fastapi_request_validation status_code=422" in line for line in strategy_http_logs(caplog))


@pytest.mark.parametrize("error,category",[
    (StrategyValidationError(["PRIVATE STRUCTURAL DETAIL"]),"strategy_structural_validation"),
    (StrategyGenerationError("PRIVATE GENERATION DETAIL"),"strategy_generation_validation"),
    (StrategyQualityError([StrategyQualityIssue("strategy.approach_restates_direction","PRIVATE QUALITY DETAIL","approach")]),"strategy_quality_validation"),
])
def test_typed_generation_422_categories_are_safe(api,caplog,monkeypatch,error,category):
    client,_,capability,_=api
    caplog.set_level(logging.WARNING,logger="uvicorn.error")
    monkeypatch.setattr(capability,"generate",lambda *_,**__: (_ for _ in ()).throw(error))

    response=client.post(
        "/personal/decisions/10000000-0000-4000-8000-000000000041/strategy",
        headers=HEADERS,json={"title":"PRIVATE STRATEGY TITLE"},
    )

    logs=strategy_http_logs(caplog); rendered=" ".join(logs)
    assert response.status_code==422
    assert any(f"category={category} status_code=422" in line for line in logs)
    if isinstance(error,StrategyGenerationError):
        assert any("generation_codes=strategy_generation.invalid_output" in line for line in logs)
    assert any("strategy_http_stage=orchestrator_entered" in line for line in logs)
    assert "PRIVATE" not in rendered


def test_application_validation_422_is_pre_orchestrator_and_safe(api,caplog,monkeypatch):
    client,_,_,_=api
    caplog.set_level(logging.WARNING,logger="uvicorn.error")
    def reject(*_,**__): raise StrategyApplicationValidationError("PRIVATE APPLICATION DETAIL")
    monkeypatch.setattr(personal_decision_routes.strategy_application_service,"generate_and_persist_idempotent_decision_strategy",reject)

    response=client.post(
        "/personal/decisions/10000000-0000-4000-8000-000000000041/strategy",
        headers=HEADERS,json={"title":"PRIVATE STRATEGY TITLE"},
    )

    logs=strategy_http_logs(caplog); rendered=" ".join(logs)
    assert response.status_code==422
    assert any("category=application_validation status_code=422" in line for line in logs)
    assert not any("strategy_http_stage=orchestrator_entered" in line for line in logs)
    assert "PRIVATE" not in rendered


def test_adapter_validation_422_is_pre_orchestrator_and_safe(api,caplog,monkeypatch):
    client,_,_,_=api
    caplog.set_level(logging.WARNING,logger="uvicorn.error")
    def reject(*_,**__): raise StrategyValidationError(["PRIVATE ADAPTER DETAIL"])
    monkeypatch.setattr(personal_decision_routes,"build_strategy_input_from_snapshot",reject)

    response=client.post(
        "/personal/decisions/10000000-0000-4000-8000-000000000041/strategy",
        headers=HEADERS,json={"title":"PRIVATE STRATEGY TITLE"},
    )

    logs=strategy_http_logs(caplog); rendered=" ".join(logs)
    assert response.status_code==422
    assert any("category=adapter_validation status_code=422" in line for line in logs)
    assert not any("strategy_http_stage=generation_entered" in line for line in logs)
    assert not any("strategy_http_stage=orchestrator_entered" in line for line in logs)
    assert "PRIVATE" not in rendered


def test_strategy_input_validation_cause_is_distinct_and_safe(api,caplog,monkeypatch):
    client,_,_,_=api
    caplog.set_level(logging.WARNING,logger="uvicorn.error")
    def reject(*_,**__):
        cause=StrategyValidationError(["PRIVATE INPUT DETAIL"])
        raise StrategyApplicationValidationError("PRIVATE APPLICATION DETAIL") from cause
    monkeypatch.setattr(personal_decision_routes.strategy_application_service,"generate_and_persist_idempotent_decision_strategy",reject)

    response=client.post(
        "/personal/decisions/10000000-0000-4000-8000-000000000041/strategy",
        headers=HEADERS,json={"title":"PRIVATE STRATEGY TITLE"},
    )

    logs=strategy_http_logs(caplog); rendered=" ".join(logs)
    assert response.status_code==422
    assert any("category=strategy_input_validation status_code=422" in line for line in logs)
    assert not any("strategy_http_stage=orchestrator_entered" in line for line in logs)
    assert "PRIVATE" not in rendered
