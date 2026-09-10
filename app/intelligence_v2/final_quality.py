"""Deterministic user-facing Decision Brief normalization and quality gate."""
from __future__ import annotations

import logging
import re
import time

logger=logging.getLogger("uvicorn.error")


class FinalBriefQualityError(RuntimeError):
    """A required user-facing section could not be safely repaired."""

    def __init__(self, categories):
        self.categories = tuple(dict.fromkeys(categories))
        super().__init__("final decision brief failed quality validation")
_INTERNAL_ID=re.compile(r"\[?(?:user-query|(?:derived|memory|document(?:-chunk)?):[\w.-]+)\]?",re.I)
_MACHINE_PREFIX=re.compile(r"^[a-z][a-z0-9]*_[a-z0-9_]+:\s*",re.I)
_INSTRUCTION=re.compile(r"\b(?:give|provide|show|tell|explain|include|write|create)\s+(?:me|us)\b|\bplease\b",re.I)
_DANGLING=re.compile(r"(?:[,;:]|\b(?:and|or|but|because|then|doing|with|to))\s*$",re.I)
_SCRIPT=re.compile(r"[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af]")
_MOJIBAKE=re.compile(r"(?:Ã.|Â.|â[\x80-\xbf]|å.{0,5}ä)")

def _unexpected_language(text,source):
    source_has_script=bool(_SCRIPT.search(source)); requested=bool(re.search(r"\b(?:translate|in (?:chinese|japanese|korean)|multilingual)\b",source,re.I))
    return not source_has_script and not requested and bool(_SCRIPT.search(text) or _MOJIBAKE.search(text))

def _clean(value,source,*,optional=True):
    if not isinstance(value,str): return ""
    text=_MACHINE_PREFIX.sub("",_INTERNAL_ID.sub("",value)).strip(" \t\r\n-•")
    text=re.sub(r"\s+([,.;:!?])",r"\1",text);text=re.sub(r"\s{2,}"," ",text).strip()
    if _INSTRUCTION.search(text): return ""
    if _unexpected_language(text,source):
        if optional:return ""
        text=_SCRIPT.sub("",text);text=_MOJIBAKE.sub("",text);text=re.sub(r"\s{2,}"," ",text).strip()
    if not text or _DANGLING.search(text): return ""
    return text

def _list(values,source):
    result=[]
    for value in values or []:
        clean=_clean(value,source)
        if clean and clean.lower() not in {item.lower() for item in result}:result.append(clean)
    return result

def _known(state,source):
    facts=state.request.source_metadata.get("fact_ledger",{}).get("facts",[]);result=[]
    for fact in facts:
        label=str(fact.get("type","")).replace("_"," ").strip().capitalize();value=_clean(str(fact.get("value","")).strip(),source,optional=False)
        item=f"{label}: {value}" if label and value else value
        if item and item.lower() not in {prior.lower() for prior in result}:result.append(item)
    return result

def finalize_decision_brief(response,state):
    started=time.perf_counter();source=state.request.user_query;failures=[]
    logger.warning("final_quality_stage=started")
    response["key_facts"]=_known(state,source)
    for key in ("derived_facts","risks","goals","decision_drivers","uncertainties","prioritized_actions","what_would_change_recommendation","limitations"):
        response[key]=_list(response.get(key),source)
    alternatives=[]
    for item in response.get("alternatives",[]):
        option=_clean(item.get("option"),source,optional=False)
        if not option:continue
        normalized={**item,"option":option,"benefits":_list(item.get("benefits"),source),"downsides":_list(item.get("downsides"),source),"assumptions":_list(item.get("assumptions"),source),"conditions_for_success":_list(item.get("conditions_for_success"),source)}
        alternatives.append(normalized)
    response["alternatives"]=alternatives
    recommendation=response.get("recommendation",{});recommendation["recommended_option"]=_clean(recommendation.get("recommended_option"),source,optional=False);recommendation["rationale"]=_clean(recommendation.get("rationale"),source,optional=False)
    recommendation["prerequisites"]=_list(recommendation.get("prerequisites"),source);recommendation["what_would_change_the_recommendation"]=_list(recommendation.get("what_would_change_the_recommendation"),source)
    response["analysis"]=_clean(response.get("analysis"),source,optional=False);response["problem_understanding"]=_clean(response.get("problem_understanding"),source,optional=False)
    unknown=_list([*(response.get("evidence_quality",{}).get("unknown",[])),*(response.get("unresolved_questions",[]))],source)
    response["evidence_quality"]={"known":response["key_facts"],"derived":response["derived_facts"],"assumed":_list(response.get("assumptions"),source),"unknown":unknown}
    response["assumptions"]=response["evidence_quality"]["assumed"]
    response["unresolved_questions"]=_list(response.get("unresolved_questions"),source)
    deliverables=response.get("requested_deliverables",{});plan=response.get("decision_plan",{})
    if not recommendation.get("recommended_option") or not recommendation.get("rationale"):failures.append("malformed_required_section")
    if deliverables.get("tradeoffs") and not any(item.get("benefits") or item.get("downsides") for item in alternatives):failures.append("missing_tradeoffs")
    if deliverables.get("assumptions") and not response["assumptions"]:failures.append("missing_assumptions")
    if deliverables.get("uncertainty") and not unknown:failures.append("missing_uncertainty")
    if deliverables.get("risks") and not response["risks"]:failures.append("missing_risks")
    if deliverables.get("ranking") and len(alternatives)<2:failures.append("missing_ranking")
    if deliverables.get("next_steps") and not response["prioritized_actions"]:failures.append("missing_next_steps")
    if deliverables.get("change_triggers") and not recommendation.get("what_would_change_the_recommendation"):failures.append("missing_change_conditions")
    horizon=deliverables.get("plan_horizon")
    if horizon and (not plan.get("phases") or plan.get("horizon_value")!=horizon.get("value") or plan.get("horizon_unit")!=horizon.get("unit")):failures.append("missing_requested_plan")
    elapsed=round((time.perf_counter()-started)*1000,3);response.setdefault("telemetry",{})["final_quality_ms"]=elapsed
    response["completeness"].update({"recommendation":bool(recommendation.get("recommended_option") and recommendation.get("rationale")),"tradeoffs":not deliverables.get("tradeoffs") or bool(alternatives),"assumptions":not deliverables.get("assumptions") or bool(response["assumptions"]),"uncertainty":not deliverables.get("uncertainty") or bool(unknown),"risks":not deliverables.get("risks") or bool(response["risks"]),"ranking":not deliverables.get("ranking") or len(alternatives)>=2,"next_steps":not deliverables.get("next_steps") or bool(response["prioritized_actions"]),"change_triggers":not deliverables.get("change_triggers") or bool(recommendation.get("what_would_change_the_recommendation")),"plan":not horizon or bool(plan.get("phases"))})
    if failures:
        logger.warning("final_quality_stage=failed failure_category=%s",",".join(sorted(set(failures))))
        raise FinalBriefQualityError(failures)
    logger.warning("final_quality_stage=passed")
    return response
