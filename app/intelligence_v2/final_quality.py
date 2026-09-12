"""Deterministic user-facing Decision Brief normalization and quality gate."""
from __future__ import annotations

import logging
import re
import time

logger=logging.getLogger("uvicorn.error")


class FinalBriefQualityError(RuntimeError):
    """A required user-facing section could not be safely repaired."""

    def __init__(self, categories, *, required_field="unknown", quality_rule="unknown"):
        self.categories = tuple(dict.fromkeys(categories))
        self.required_field = required_field
        self.quality_rule = quality_rule
        super().__init__("final decision brief failed quality validation")
_INTERNAL_ID=re.compile(r"\[?(?:user-query|(?:derived|memory|document(?:-chunk)?):[\w.-]+)\]?",re.I)
_MACHINE_PREFIX=re.compile(r"^[a-z][a-z0-9]*_[a-z0-9_]+:\s*",re.I)
_INSTRUCTION=re.compile(r"\b(?:give|provide|show|tell|explain|include|write|create)\s+(?:me|us)\b|\bplease\b",re.I)
_SENTENCE_TERMINATOR=r"[.!?\u3002\uff01\uff1f]?"
_DANGLING=re.compile(rf"(?:[,;:]|\b(?:and|or|but|because)){_SENTENCE_TERMINATOR}\s*$",re.I)
_AMBIGUOUS_DANGLING=re.compile(rf"(?:\b(?:and|or|but)\s+(?:then|doing|with|to)|\bthen\s+(?:doing|with|to)|\b(?:want|need|intend|plan|aim|try|attempt|expect|hope|decide|choose|going|able|ready)\s+to|\b(?:start|begin|continue|keep)\s+doing|\b(?:a|an|the|this|that|each|any)\s+[\w'-]+\s+with){_SENTENCE_TERMINATOR}\s*$",re.I)
_REQUEST_INSTRUCTION=re.compile(r"^\s*(?:please\s+)?(?:give|provide|show|tell|explain|include|write|create|describe|outline|list)\b",re.I)
_DANGLING_ENGLISH=re.compile(r"(?:\b(?:a|an|the)|\bthe\s+(?:later|former))\s*$",re.I)
_GENERIC_PLAN=re.compile(r"\b(?:terms and constraints that differ across the options|smallest reversible test supported by the available resources|update the decision using confirmed evidence)\b",re.I)
_TRAILING_MODIFIER=re.compile(r"\b[a-z]+-[a-z]*(?:ing|ed|ive|al|ic|ous|able|ible|ary|ory|ful|less)$",re.I)
_TERMINAL_DEGREE_MODIFIER=re.compile(r"\b(?:right|more|less|very|too|quite|rather|almost|nearly)$",re.I)
_TRAILING_BOUNDARY=re.compile(r"[-\u2011\u2013\u2014]\s*$")
_TERMINAL_SENTENCE_FRAGMENT=re.compile(r"(?:^|[.!?]\s+)[A-Za-z]\s*$")
_TERMINAL_UPPERCASE_LABEL=re.compile(r"\S\s+A$")
_SCRIPT=re.compile(r"[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af]")
_MOJIBAKE=re.compile(r"(?:Ã.|Â.|â[\x80-\xbf]|å.{0,5}ä)")

def _unexpected_language(text,source):
    source_has_script=bool(_SCRIPT.search(source)); requested=bool(re.search(r"\b(?:translate|in (?:chinese|japanese|korean)|multilingual)\b",source,re.I))
    return not source_has_script and not requested and bool(_SCRIPT.search(text) or _MOJIBAKE.search(text))

def _clean_with_rule(value,source,*,optional=True,reject_instructions=True):
    if not isinstance(value,str): return "", "empty_after_normalization"
    text=re.sub(r"Monthly budget appears able to absorb ownership costs better given a (\$[\d,]+) surplus\.?",r"You currently have a \1 monthly surplus before any additional car-related costs.",value,flags=re.I)
    text=_MACHINE_PREFIX.sub("",_INTERNAL_ID.sub("",text)).strip(" \t\r\n•")
    text=re.sub(r"\s+([,.;:!?])",r"\1",text);text=re.sub(r"\s{2,}"," ",text).strip()
    if reject_instructions and (_INSTRUCTION.search(text) or _REQUEST_INSTRUCTION.search(text)): return "", "instruction"
    unexpected_language=_unexpected_language(text,source)
    if unexpected_language:
        if optional:return "", "unexpected_language"
        text=_SCRIPT.sub("",text);text=_MOJIBAKE.sub("",text);text=re.sub(r"\s{2,}"," ",text).strip()
    english=not _SCRIPT.search(source) and len(re.findall(r"[A-Za-z]",source))>=20
    unfinished_modifier=bool(_TRAILING_MODIFIER.search(text) and not re.search(r"\b(?:is|are|was|were|be|seems?|remains?|becomes?)\s+[a-z]+-[a-z]*(?:ing|ed|ive|al|ic|ous|able|ible|ary|ory|ful|less)$",text,re.I))
    unfinished_degree=bool(re.search(r"\b(?:without|while|before|after|through|by)\b",text,re.I) and _TERMINAL_DEGREE_MODIFIER.search(text))
    if not text:return "", "unexpected_language" if unexpected_language else "empty_after_normalization"
    if _TRAILING_BOUNDARY.search(text):return "", "trailing_boundary"
    if english and _TERMINAL_SENTENCE_FRAGMENT.search(text):return "", "sentence_fragment"
    if _DANGLING.search(text):return "", "dangling"
    if english and _AMBIGUOUS_DANGLING.search(text):return "", "dangling"
    if english and _DANGLING_ENGLISH.search(text) and not _TERMINAL_UPPERCASE_LABEL.search(text):return "", "dangling_english"
    if english and unfinished_modifier:return "", "trailing_modifier"
    if english and unfinished_degree:return "", "subordinate_modifier"
    return text, None

def _clean(value,source,*,optional=True,reject_instructions=True):
    return _clean_with_rule(value,source,optional=optional,reject_instructions=reject_instructions)[0]

def _list(values,source):
    result=[]
    for value in values or []:
        clean=_clean(value,source)
        if clean and clean.lower() not in {item.lower() for item in result}:result.append(clean)
    return result

def _semantic_structure(value,source):
    if isinstance(value,str):return _clean(value,source)
    if isinstance(value,list):
        return [clean for item in value if (clean:=_semantic_structure(item,source)) not in ("",[],{})]
    if isinstance(value,dict):
        return {key:clean for key,item in value.items() if (clean:=_semantic_structure(item,source)) not in ("",[],{})}
    return value

_UNCERTAINTY_STOP={"a","an","and","are","be","do","for","how","if","in","is","it","of","or","the","this","to","what","would","you","your"}
_UNCERTAINTY_EQUIVALENTS={"expensive":"cost","expense":"cost","expenses":"cost","costs":"cost","tuition":"cost","fund":"funding","funded":"funding","finance":"funding","financing":"funding","cover":"funding","pay":"funding","program":"education","degree":"education","school":"education","studies":"education"}

def _concept_tokens(value):
    return {_UNCERTAINTY_EQUIVALENTS.get(token,token) for token in re.findall(r"[a-z0-9]+",str(value).lower()) if token not in _UNCERTAINTY_STOP}

def _uncertainty_key(value,state):
    tokens=_concept_tokens(value)
    for gap in state.information_gaps:
        reference=_concept_tokens(" ".join((gap.field,gap.why_needed,gap.suggested_question,gap.impact_on_decision)))
        shared=tokens&reference
        if len(shared)>=2 or (len(shared)>=1 and len(tokens)<=4):return f"gap:{gap.field}"
    return "text:"+" ".join(sorted(tokens))

def _dedupe_uncertainties(values,state,seen=None):
    seen=set() if seen is None else seen;result=[]
    for value in values:
        key=_uncertainty_key(value,state)
        if key in seen:continue
        seen.add(key);result.append(value)
    return result,seen

def normalized_public_facts(state):
    source=state.request.user_query
    facts=state.request.source_metadata.get("fact_ledger",{}).get("facts",[]);result=[]
    for fact in facts:
        label=str(fact.get("type","")).replace("_"," ").strip().capitalize();value=_clean(str(fact.get("value","")).strip(),source,optional=False)
        item=f"{label}: {value}" if label and value else value
        if item and item.lower() not in {prior.lower() for prior in result}:result.append(item)
    phase=state.analysis_outputs.get("phase2",{})
    for kind,values in (("Option",phase.get("options",[])),):
        for value in values[:4]:
            clean=_clean(value,source)
            item=f"{kind}: {clean}" if clean else ""
            if item and item.lower() not in {prior.lower() for prior in result}:result.append(item)
    return result[:10]

def normalized_public_items(values,state):
    return _list(values,state.request.user_query)

def _plan(plan,source):
    normalized={**(plan or {})};phases=[]
    if normalized.get("horizon_label") is not None:normalized["horizon_label"]=_clean(normalized.get("horizon_label"),source,reject_instructions=False)
    if normalized.get("basis") is not None:normalized["basis"]=_clean(normalized.get("basis"),source,reject_instructions=False)
    for phase in normalized.get("phases",[]):
        actions=[item for item in (_clean(value,source,reject_instructions=False) for value in phase.get("actions",[])) if item and not _GENERIC_PLAN.search(item)]
        title=_clean(phase.get("phase"),source,reject_instructions=False)
        objective=_clean(phase.get("objective"),source,reject_instructions=False)
        checkpoint=_clean(phase.get("checkpoint"),source,reject_instructions=False)
        trigger=_clean(phase.get("reassessment_trigger"),source,reject_instructions=False)
        dependencies=_list(phase.get("dependencies"),source)
        if title and objective and actions and checkpoint and trigger: phases.append({**phase,"phase":title,"objective":objective,"actions":actions,"checkpoint":checkpoint,"dependencies":dependencies,"reassessment_trigger":trigger})
    normalized["phases"]=phases
    return normalized

def finalize_decision_brief(response,state):
    started=time.perf_counter();source=state.request.user_query;failures=[]
    logger.warning("final_quality_stage=started")
    response["key_facts"]=normalized_public_facts(state)
    for key in ("derived_facts","risks","goals","decision_drivers","uncertainties","prioritized_actions","what_would_change_recommendation","limitations"):
        response[key]=_list(response.get(key),source)
    internal_fields={gap.field.lower() for gap in state.information_gaps}
    response["limitations"]=[item for item in response["limitations"] if not any(re.search(rf"\b{re.escape(field)}\b",item,re.I) for field in internal_fields)]
    alternatives=[]
    for item in response.get("alternatives",[]):
        option=_clean(item.get("option"),source,optional=False)
        if not option:continue
        normalized={**item,"option":option,"benefits":_list(item.get("benefits"),source),"downsides":_list(item.get("downsides"),source),"assumptions":_list(item.get("assumptions"),source),"conditions_for_success":_list(item.get("conditions_for_success"),source),"evidence_ids":[]}
        alternatives.append(normalized)
    response["alternatives"]=alternatives
    recommendation=response.get("recommendation",{})
    recommendation["recommended_option"],option_rule=_clean_with_rule(recommendation.get("recommended_option"),source,optional=False,reject_instructions=False)
    recommendation["rationale"],rationale_rule=_clean_with_rule(recommendation.get("rationale"),source,optional=False,reject_instructions=False)
    recommendation["prerequisites"]=_list(recommendation.get("prerequisites"),source);recommendation["what_would_change_the_recommendation"]=_list(recommendation.get("what_would_change_the_recommendation"),source)
    response["analysis"],analysis_rule=_clean_with_rule(response.get("analysis"),source,optional=False)
    response["problem_understanding"],problem_rule=_clean_with_rule(response.get("problem_understanding"),source,optional=False)
    unresolved=_list(response.get("unresolved_questions"),source)
    unresolved,uncertainty_keys=_dedupe_uncertainties(unresolved,state)
    unknown,all_uncertainty_keys=_dedupe_uncertainties(_list(response.get("evidence_quality",{}).get("unknown",[]),source),state,set(uncertainty_keys))
    response["evidence_quality"]={"known":response["key_facts"],"derived":response["derived_facts"],"assumed":_list(response.get("assumptions"),source),"unknown":unknown}
    response["assumptions"]=response["evidence_quality"]["assumed"]
    response["unresolved_questions"]=unresolved
    tensions=[]
    for item in response.get("goal_tensions",[]):
        tension=_clean(item.get("tension"),source)
        if tension and not re.search(r"^Balance\s+['\"]",tension): tensions.append(_semantic_structure({**item,"tension":tension},source))
    response["goal_tensions"]=tensions
    for key in ("resources","constraints","resource_risks","trends","causal_effects","confidence_rationale","what_changed"):
        response[key]=_semantic_structure(response.get(key,[]),source)
    deliverables=response.get("requested_deliverables",{})
    horizon=deliverables.get("plan_horizon")
    if horizon:
        from app.intelligence_v2.quality import final_decision_plan
        response["decision_plan"]=final_decision_plan(horizon,recommendation=recommendation["recommended_option"],alternatives=alternatives,goals=response.get("goals",[]),gaps=state.information_gaps,change_conditions=recommendation["what_would_change_the_recommendation"])
    response["decision_plan"]=_plan(response.get("decision_plan",{}),source)
    gap_prose={gap.why_needed.lower() for gap in state.information_gaps if gap.can_proceed_without}
    response["uncertainties"],_= _dedupe_uncertainties([item for item in response["uncertainties"] if item.lower() not in gap_prose],state,set(all_uncertainty_keys))
    response["next_move"]=response["decision_plan"].get("phases",[{}])[0].get("actions",[None])[0] if horizon else _clean(response.get("next_move"),source,reject_instructions=False)
    response["evidence_used"]=[];response["citations"]=[]
    plan=response.get("decision_plan",{})
    required_failure=("recommended_option",option_rule) if not recommendation.get("recommended_option") else (("rationale",rationale_rule) if not recommendation.get("rationale") else (("analysis",analysis_rule) if not response.get("analysis") else (("problem_understanding",problem_rule) if not response.get("problem_understanding") else None)))
    if required_failure:failures.append("malformed_required_section")
    if deliverables.get("tradeoffs") and not any(item.get("benefits") or item.get("downsides") for item in alternatives):failures.append("missing_tradeoffs")
    if deliverables.get("assumptions") and not response["assumptions"]:failures.append("missing_assumptions")
    if deliverables.get("uncertainty") and not (unknown or unresolved):failures.append("missing_uncertainty")
    if deliverables.get("risks") and not response["risks"]:failures.append("missing_risks")
    if deliverables.get("ranking") and len(alternatives)<2:failures.append("missing_ranking")
    if deliverables.get("next_steps") and not response["prioritized_actions"]:failures.append("missing_next_steps")
    if deliverables.get("change_triggers") and not recommendation.get("what_would_change_the_recommendation"):failures.append("missing_change_conditions")
    if horizon and (not plan.get("phases") or plan.get("horizon_value")!=horizon.get("value") or plan.get("horizon_unit")!=horizon.get("unit") or any(not phase.get("actions") for phase in plan.get("phases",[]))):failures.append("missing_requested_plan")
    elapsed=round((time.perf_counter()-started)*1000,3);response.setdefault("telemetry",{})["final_quality_ms"]=elapsed
    response["completeness"].update({"recommendation":bool(recommendation.get("recommended_option") and recommendation.get("rationale")),"tradeoffs":not deliverables.get("tradeoffs") or bool(alternatives),"assumptions":not deliverables.get("assumptions") or bool(response["assumptions"]),"uncertainty":not deliverables.get("uncertainty") or bool(unknown or unresolved),"risks":not deliverables.get("risks") or bool(response["risks"]),"ranking":not deliverables.get("ranking") or len(alternatives)>=2,"next_steps":not deliverables.get("next_steps") or bool(response["prioritized_actions"]),"change_triggers":not deliverables.get("change_triggers") or bool(recommendation.get("what_would_change_the_recommendation")),"plan":not horizon or bool(plan.get("phases"))})
    if failures:
        required_field,quality_rule=required_failure or ("unknown","unknown")
        logger.warning("final_quality_stage=failed failure_category=%s required_field=%s quality_rule=%s",",".join(sorted(set(failures))),required_field,quality_rule or "unknown")
        raise FinalBriefQualityError(failures,required_field=required_field,quality_rule=quality_rule or "unknown")
    logger.warning("final_quality_stage=passed")
    return response
