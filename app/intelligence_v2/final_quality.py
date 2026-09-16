"""Deterministic user-facing Decision Brief normalization and quality gate."""
from __future__ import annotations

import logging
import re
import time
from enum import Enum

from app.intelligence_v2.model_provider import InvalidModelResponseError, ProviderTimeoutError, ProviderUnavailableError, SEMANTIC_QUALITY_FIELD_IDS, SEMANTIC_QUALITY_REASONS, SEMANTIC_QUALITY_RESULTS, analysis_max_output_tokens

logger=logging.getLogger("uvicorn.error")

# Semantic roots in the canonical Personal Ask display DTO. Transport metadata
# is intentionally outside this contract. Nested dictionaries/lists below
# these roots are traversed recursively by the terminal quality gate.
DISPLAY_DTO_SEMANTIC_ROOTS=(
    "problem_understanding","analysis","key_facts","derived_facts","alternatives",
    "risks","goals","goal_tensions","resources","constraints","resource_risks",
    "trends","decision_drivers","uncertainties","causal_effects",
    "prioritized_actions","unresolved_questions","limitations","assumptions",
    "confidence_rationale","what_would_change_recommendation","recommendation",
    "evidence_quality","decision_plan","next_move","what_changed",
)


class QualitySeverity(str,Enum):
    HARD_FAILURE="hard_failure"
    RECOVERABLE="recoverable"
    FIELD_DEGRADATION="field_degradation"

class SemanticRouting(str,Enum):
    COMPLETE="complete"
    INCOMPLETE="incomplete"
    AMBIGUOUS="ambiguous"


class FinalBriefQualityError(RuntimeError):
    """A required user-facing section could not be safely repaired."""

    def __init__(self, categories, *, required_field="unknown", quality_rule="unknown"):
        self.categories = tuple(dict.fromkeys(categories))
        self.required_field = required_field
        self.quality_rule = quality_rule
        self.severity = QualitySeverity.HARD_FAILURE
        super().__init__("final decision brief failed quality validation")
_INTERNAL_ID=re.compile(r"\[?(?:user-query|(?:derived|memory|document(?:-chunk)?):[\w.-]+)\]?",re.I)
_MACHINE_PREFIX=re.compile(r"^[a-z][a-z0-9]*_[a-z0-9_]+:\s*",re.I)
_INSTRUCTION=re.compile(r"\b(?:give|provide|show|tell|explain|include|write|create)\s+(?:me|us)\b|\bplease\b",re.I)
_SENTENCE_TERMINATOR=r"[.!?\u3002\uff01\uff1f]?"
_DANGLING=re.compile(rf"(?:[,;:]|\b(?:and|or|but|because)){_SENTENCE_TERMINATOR}\s*$",re.I)
_AMBIGUOUS_DANGLING=re.compile(rf"(?:\b(?:and|or|but)\s+(?:then|doing|with|to)|\bthen\s+(?:doing|with|to)|\b(?:want|need|intend|plan|aim|try|attempt|expect|hope|decide|choose|going|able|ready)\s+to|\b(?:start|begin|continue|keep)\s+doing|\b(?:a|an|the|this|that|each|any)\s+[\w'-]+\s+with){_SENTENCE_TERMINATOR}\s*$",re.I)
_REQUEST_INSTRUCTION=re.compile(r"^\s*(?:please\s+)?(?:give|provide|show|tell|explain|include|write|create|describe|outline|list)\b",re.I)
_GENERIC_PLAN=re.compile(r"\b(?:terms and constraints that differ across the options|smallest reversible test supported by the available resources|update the decision using confirmed evidence)\b",re.I)
_TRAILING_MODIFIER=re.compile(r"\b[a-z]+-[a-z]*(?:ing|ed|ive|al|ic|ous|able|ible|ary|ory|ful|less)$",re.I)
_TERMINAL_DEGREE_MODIFIER=re.compile(r"\b(?:right|more|less|very|too|quite|rather|almost|nearly)$",re.I)
_TRAILING_BOUNDARY=re.compile(r"[-\u2011\u2013\u2014]\s*$")
_SCRIPT=re.compile(r"[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af]")
_MOJIBAKE=re.compile(r"(?:Ã.|Â.|â[\x80-\xbf]|å.{0,5}ä)")

_OPENING_QUOTES={"\u2018":"\u2019","\u201c":"\u201d"}
_BRACKETS={"(":")","[":"]","{":"}"}
_SYMMETRIC_QUOTES={'"',"'"}
_SUBORDINATOR=re.compile(r"\b(if|when|because|although|while|unless)\b",re.I)
_ADJECTIVE_FORM=re.compile(r"^(?:full|(?![a-z'-]*(?:ment|tion|sion|ness|ity|ship|ance|ence|er|or)$)[a-z][a-z'-]*(?:al|ial|ic|ive|ous|ary|ory|able|ible|ent|ant|less|ful))$",re.I)

def _is_apostrophe(text,index):
    previous=text[index-1] if index else "";following=text[index+1] if index+1<len(text) else ""
    if previous.isalnum() and following.isalnum():return True
    if previous.isdigit():return True
    if previous.lower()=="s" and following.isspace():
        next_character=next((character for character in text[index+1:] if not character.isspace()),"")
        if next_character.isalnum():return True
    return False

def _unbalanced_pair_rule(text):
    stack=[];pairs={**_BRACKETS,**_OPENING_QUOTES};closers={value:key for key,value in pairs.items()}
    for index,character in enumerate(text):
        if character in {"'","\u2019"} and _is_apostrophe(text,index):continue
        if character=='"' and index and text[index-1]=="\\":continue
        if character in _SYMMETRIC_QUOTES:
            if stack and stack[-1]==character:stack.pop()
            else:stack.append(character)
        elif character in pairs:stack.append(character)
        elif character in closers:
            if not stack or stack.pop()!=closers[character]:return "unbalanced_quote" if character in _OPENING_QUOTES.values() else "unbalanced_bracket"
    if any(character in _OPENING_QUOTES for character in stack):return "unbalanced_quote"
    if any(character in _BRACKETS for character in stack):return "unbalanced_bracket"
    if any(character in _SYMMETRIC_QUOTES for character in stack):return "unbalanced_quote"
    return None

def _clause_has_predicate(clause,subordinator):
    clause=re.sub(r"^then\b", "", clause.strip(),flags=re.I).strip(" ,")
    words=re.findall(r"[A-Za-z][A-Za-z'-]*",clause)
    if subordinator.lower()=="while" and len(words)==1 and words[0].lower().endswith("ing"):return True
    if len(words)<2:return False
    if re.fullmatch(r"[A-Za-z'-]+\s+(?:and|or)\s+[A-Za-z'-]+",clause,re.I):return False
    if words[0].lower() in {"the","a","an","this","that","these","those","my","your","our","their","its"} and len(words)<3:return False
    return bool(re.search(r"\b(?:is|are|was|were|be|been|being|has|have|had|can|could|will|would|should|may|might|must|do|does|did)\b",clause,re.I) or any(re.search(r"(?:ed|ing|s)$",word,re.I) for word in words[1:]) or words[0].lower() not in {"the","a","an","this","that","these","those"})

def analyze_semantic_completeness(text,*,english=True):
    """Return bounded, content-free structural completeness diagnostics."""
    if not isinstance(text,str) or not text.strip():return {"complete":False,"rule":"empty_after_normalization"}
    text=text.strip();pair_rule=_unbalanced_pair_rule(text)
    if pair_rule:return {"complete":False,"rule":pair_rule}
    if not english:return {"complete":True,"rule":None}
    core=re.sub(r"[.!?\u3002\uff01\uff1f]+$","",text).strip()
    if re.search(r"(?:^|[.!?]\s+)(?:[A-Za-z]|a|an|the)\s*$",core,re.I):return {"complete":False,"rule":"sentence_fragment"}
    if re.search(r"(?:[,;:]|\b(?:and|or|but|because))$",core,re.I):return {"complete":False,"rule":"incomplete_coordination"}
    matches=list(_SUBORDINATOR.finditer(core))
    if matches:
        marker=matches[-1];tail=core[marker.end():].strip()
        if marker.start()==0:
            comma=core.find(",",marker.end())
            if comma<0 or not _clause_has_predicate(core[comma+1:],marker.group(1)):return {"complete":False,"rule":"open_conditional"}
        elif not _clause_has_predicate(tail,marker.group(1)):
            return {"complete":False,"rule":"open_conditional"}
    if re.search(r"(?:^|[,;:])\s*then$",core,re.I):return {"complete":False,"rule":"open_conditional"}
    noun_match=re.search(r"\b(a|an|the)\s+([A-Za-z][A-Za-z'-]*(?:\s+[A-Za-z][A-Za-z'-]*)*)$",core,re.I)
    if noun_match and all(_ADJECTIVE_FORM.fullmatch(word) for word in noun_match.group(2).split()):return {"complete":False,"rule":"incomplete_noun_phrase"}
    if re.search(r"\b(?:through|via)\s+self$",core,re.I):return {"complete":False,"rule":"incomplete_complement"}
    if re.search(r"\b(?:and|or|but)\s+(?:then|doing|with|to)$",core,re.I) or re.search(r"\b(?:want|need|intend|plan|aim|try|attempt|expect|hope|decide|choose|going|able|ready)\s+to$",core,re.I):return {"complete":False,"rule":"incomplete_complement"}
    if re.search(r"\b(?:start|begin|continue|keep)\s+doing$",core,re.I) or re.search(r"\b(?:a|an|the|this|that|each|any)\s+[\w'-]+\s+with$",core,re.I):return {"complete":False,"rule":"incomplete_complement"}
    article_match=re.search(r"\b(a|an|the)$",core)
    if article_match:
        prefix=core[:article_match.start()].rstrip()
        # A bare lower-case article after an object-taking predicate opens a
        # missing noun phrase. Case-significant and delimited forms remain
        # available for names, labels, grades, variables, and other designators.
        predicate=r"(?:choose|compare|evaluate|select|use|consider|pick|review|assess|prefer|take|pursue|adopt|recommend|is|are|was|were|become|becomes|became)"
        if re.search(rf"(?:^|\s){predicate}$",prefix,re.I):return {"complete":False,"rule":"incomplete_article"}
    words=re.findall(r"[A-Za-z][A-Za-z'-]*",core)
    first=next((word for word in words if word.lower() not in {"a","an","the"}),"")
    if words and words[-1].lower().endswith("ly") and _ADJECTIVE_FORM.fullmatch(first) and not re.search(r"\b(?:is|are|was|were|be|become|becomes|became|remain|remains|stays?|seems?|appears?)\b",core,re.I):return {"complete":False,"rule":"incomplete_noun_phrase"}
    return {"complete":True,"rule":None}

def _unexpected_language(text,source):
    source_has_script=bool(_SCRIPT.search(source)); requested=bool(re.search(r"\b(?:translate|in (?:chinese|japanese|korean)|multilingual)\b",source,re.I))
    return not source_has_script and not requested and bool(_SCRIPT.search(text) or _MOJIBAKE.search(text))

def _quality_severity(*,optional=False,recoverable=False):
    if recoverable:return QualitySeverity.RECOVERABLE
    return QualitySeverity.FIELD_DEGRADATION if optional else QualitySeverity.HARD_FAILURE

def _quality_event(action,field,rule,trace=None):
    logger.warning("final_quality_stage=recovered quality_action=%s required_field=%s quality_rule=%s",action,field,rule)
    if trace is not None:trace.append({"action":action,"field":field,"rule":rule})

def _semantic_event(stage,**values):
    safe={"stage":stage}
    allow={"trigger":{"boundary_recovery","recovery_cluster","output_headroom","field_length_proximity","call_budget_exhausted","none"},"field":set(SEMANTIC_QUALITY_FIELD_IDS),"result":set(SEMANTIC_QUALITY_RESULTS),"action":{"retained","degraded","safe_failure","skipped_call_budget","none"},"failure":{"timeout","unavailable","invalid_schema","none"}}
    for key,allowed in allow.items():
        value=values.get(key)
        if value in allowed:safe[key]=value
    logger.warning(" ".join([f"semantic_quality_stage={safe.pop('stage')}",*[f"semantic_quality_{key}={value}" for key,value in safe.items()]]))

def _clean_with_rule(value,source,*,optional=True,reject_instructions=True,reject_source_copy=False,field="unknown",allow_recovery=True,trace=None):
    if not isinstance(value,str): return "", "empty_after_normalization"
    text=re.sub(r"Monthly budget appears able to absorb ownership costs better given a (\$[\d,]+) surplus\.?",r"You currently have a \1 monthly surplus before any additional car-related costs.",value,flags=re.I)
    text=_MACHINE_PREFIX.sub("",_INTERNAL_ID.sub("",text)).strip(" \t\r\n•")
    text=re.sub(r"\s+([,.;:!?])",r"\1",text);text=re.sub(r"\s{2,}"," ",text).strip()
    collapsed=re.sub(r"([.!?])\1+$",r"\1",text)
    if collapsed!=text:
        text=collapsed
        if allow_recovery:_quality_event("repaired",field,"duplicate_punctuation",trace)
    normalized_source=re.sub(r"\s+"," ",str(source)).strip()
    if reject_source_copy and text==normalized_source:return "", "source_copy"
    if reject_instructions and (_INSTRUCTION.search(text) or _REQUEST_INSTRUCTION.search(text)): return "", "instruction"
    unexpected_language=_unexpected_language(text,source)
    if unexpected_language:
        if optional:return "", "unexpected_language"
        text=_SCRIPT.sub("",text);text=_MOJIBAKE.sub("",text);text=re.sub(r"\s{2,}"," ",text).strip()
    english=not _SCRIPT.search(source) and len(re.findall(r"[A-Za-z]",source))>=20
    unfinished_modifier=bool(_TRAILING_MODIFIER.search(text) and not re.search(r"\b(?:is|are|was|were|be|seems?|remains?|becomes?)\s+[a-z]+-[a-z]*(?:ing|ed|ive|al|ic|ous|able|ible|ary|ory|ful|less)$",text,re.I))
    unfinished_degree=bool(re.search(r"\b(?:without|while|before|after|through|by)\b",text,re.I) and _TERMINAL_DEGREE_MODIFIER.search(text))
    if not text:return "", "unexpected_language" if unexpected_language else "empty_after_normalization"
    structure=analyze_semantic_completeness(text,english=english)
    if not structure["complete"]:return "", structure["rule"]
    if _TRAILING_BOUNDARY.search(text):
        candidate=_TRAILING_BOUNDARY.sub("",text).rstrip()
        if _quality_severity(recoverable=allow_recovery) is QualitySeverity.RECOVERABLE and candidate:
            repaired,_=_clean_with_rule(candidate,source,optional=optional,reject_instructions=reject_instructions,reject_source_copy=reject_source_copy,field=field,allow_recovery=False,trace=trace)
            if repaired:
                _quality_event("repaired",field,"trailing_boundary",trace)
                return repaired,None
        return "", "trailing_boundary"
    if _DANGLING.search(text):return "", "dangling"
    if english and _AMBIGUOUS_DANGLING.search(text):return "", "dangling"
    if english and unfinished_modifier:return "", "trailing_modifier"
    if english and unfinished_degree:return "", "subordinate_modifier"
    return text, None

def _clean(value,source,*,optional=True,reject_instructions=True,reject_source_copy=False,field="unknown"):
    return _clean_with_rule(value,source,optional=optional,reject_instructions=reject_instructions,reject_source_copy=reject_source_copy,field=field)[0]

def _list(values,source,field="optional_item",reject_source_copy=False,trace=None):
    result=[]
    for value in values or []:
        clean,rule=_clean_with_rule(value,source,reject_source_copy=reject_source_copy,field=field,trace=trace)
        if clean and clean.lower() not in {item.lower() for item in result}:result.append(clean)
        elif clean and _quality_severity(optional=True) is QualitySeverity.FIELD_DEGRADATION:_quality_event("degraded",field,"duplicate_item",trace)
        elif rule and _quality_severity(optional=True) is QualitySeverity.FIELD_DEGRADATION:_quality_event("degraded",field,rule,trace)
    return result

_SEMANTIC_MAX_LENGTH={"problem_understanding":280,"recommended_option":200,"rationale":600,"alternative_option":160,"alternative_benefit":180,"alternative_downside":180,"condition_for_success":180,"risk":180,"unresolved_question":180,"recommendation_change_condition":180}

def _semantic_candidates(response):
    result=[]
    def add(field_id,value,path,optional,index):
        if isinstance(value,str) and value.strip():result.append({"field_id":field_id,"item_index":index,"text":value,"path":path,"optional":optional})
    add("problem_understanding",response.get("problem_understanding"),("problem_understanding",),False,0)
    recommendation=response.get("recommendation",{})
    add("recommended_option",recommendation.get("recommended_option"),("recommendation","recommended_option"),False,0)
    add("rationale",recommendation.get("rationale"),("recommendation","rationale"),False,0)
    indexes={field:0 for field in SEMANTIC_QUALITY_FIELD_IDS}
    for alternative_index,alternative in enumerate(response.get("alternatives",[])):
        field="alternative_option";add(field,alternative.get("option"),("alternatives",alternative_index,"option"),False,indexes[field]);indexes[field]+=1
        for key,field in (("benefits","alternative_benefit"),("downsides","alternative_downside"),("conditions_for_success","condition_for_success")):
            for item_index,item in enumerate(alternative.get(key,[])):
                add(field,item,("alternatives",alternative_index,key,item_index),True,indexes[field]);indexes[field]+=1
    for key,field in (("risks","risk"),("unresolved_questions","unresolved_question")):
        for item_index,item in enumerate(response.get(key,[])):
            add(field,item,(key,item_index),True,indexes[field]);indexes[field]+=1
    for item_index,item in enumerate(recommendation.get("what_would_change_the_recommendation",[])):
        field="recommendation_change_condition";add(field,item,("recommendation","what_would_change_the_recommendation",item_index),True,indexes[field]);indexes[field]+=1
    return result

def route_semantic_ambiguity(response,trace,usage):
    candidates=_semantic_candidates(response);triggers=[]
    boundary_fields={event["field"] for event in trace if event["action"]=="repaired" and event["rule"]=="trailing_boundary"}
    field_map={"problem_understanding":"problem_understanding","recommended_option":"recommended_option","rationale":"rationale","benefits":"alternative_benefit","downsides":"alternative_downside","conditions_for_success":"condition_for_success","risks":"risk","unresolved_questions":"unresolved_question","recommendation_change_conditions":"recommendation_change_condition"}
    ambiguous=set()
    for candidate_index,candidate in enumerate(candidates):
        if candidate["field_id"] in {field_map.get(field) for field in boundary_fields}:ambiguous.add(candidate_index)
        maximum=_SEMANTIC_MAX_LENGTH[candidate["field_id"]]
        if len(candidate["text"])>=int(maximum*.9):ambiguous.add(candidate_index);triggers.append("field_length_proximity")
    if boundary_fields:triggers.append("boundary_recovery")
    independent={(event["field"],event["rule"]) for event in trace}
    if len(independent)>=2:ambiguous.update(range(len(candidates)));triggers.append("recovery_cluster")
    output_tokens=usage.get("output_tokens")
    if isinstance(output_tokens,int) and output_tokens>=int(analysis_max_output_tokens()*.9):ambiguous.update(range(len(candidates)));triggers.append("output_headroom")
    return SemanticRouting.AMBIGUOUS if ambiguous else SemanticRouting.COMPLETE,[candidates[index] for index in sorted(ambiguous)],list(dict.fromkeys(triggers))

def _validate_semantic_results(raw,candidates):
    if not isinstance(raw,dict) or not isinstance(raw.get("results"),list) or len(raw["results"])!=len(candidates):raise ValueError("invalid semantic classifier schema")
    expected={(item["field_id"],item["item_index"]) for item in candidates};seen=set();result={}
    for item in raw["results"]:
        if not isinstance(item,dict) or set(item)!={"field_id","item_index","result","reason"}:raise ValueError("invalid semantic classifier schema")
        key=(item["field_id"],item["item_index"])
        if key not in expected or key in seen or item["result"] not in SEMANTIC_QUALITY_RESULTS or item["reason"] not in SEMANTIC_QUALITY_REASONS:raise ValueError("invalid semantic classifier schema")
        seen.add(key);result[key]=item
    return result

def _remove_semantic_paths(response,paths):
    for path in sorted(paths,key=lambda value:tuple(str(item) for item in value),reverse=True):
        parent=response
        for key in path[:-1]:parent=parent[key]
        last=path[-1]
        if isinstance(last,int):parent.pop(last)
        else:parent.pop(last,None)

def _semantic_structure(value,source):
    if isinstance(value,str):return _clean(value,source)
    if isinstance(value,list):
        return [clean for item in value if (clean:=_semantic_structure(item,source)) not in ("",[],{})]
    if isinstance(value,dict):
        return {key:clean for key,item in value.items() if (clean:=_semantic_structure(item,source)) not in ("",[],{})}
    return value

def _final_semantic_failure(response,source):
    fields={field:response.get(field) for field in DISPLAY_DTO_SEMANTIC_ROOTS}
    def visit(value):
        if isinstance(value,str):
            if not value.strip():return None
            english=not _SCRIPT.search(source) and len(re.findall(r"[A-Za-z]",source))>=20
            result=analyze_semantic_completeness(value,english=english)
            return result["rule"] if not result["complete"] else None
        if isinstance(value,list):return next((rule for item in value if (rule:=visit(item))),None)
        if isinstance(value,dict):return next((rule for item in value.values() if (rule:=visit(item))),None)
        return None
    for field,value in fields.items():
        if rule:=visit(value):return field,rule
    return None

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

def finalize_decision_brief(response,state,*,semantic_classifier=None,generation_usage=None):
    started=time.perf_counter();source=state.request.user_query;failures=[];quality_trace=[];generation_usage=generation_usage or {}
    logger.warning("final_quality_stage=started")
    response["key_facts"]=normalized_public_facts(state)
    for key in ("derived_facts","risks","goals","decision_drivers","uncertainties","prioritized_actions","limitations"):
        response[key]=_list(response.get(key),source,key,reject_source_copy=True,trace=quality_trace if key in {"risks","unresolved_questions"} else None)
    internal_fields={gap.field.lower() for gap in state.information_gaps}
    response["limitations"]=[item for item in response["limitations"] if not any(re.search(rf"\b{re.escape(field)}\b",item,re.I) for field in internal_fields)]
    alternatives=[]
    for item in response.get("alternatives",[]):
        option=_clean_with_rule(item.get("option"),source,optional=False,reject_source_copy=True,field="alternative_option",trace=quality_trace)[0]
        if not option:continue
        normalized={**item,"option":option,"benefits":_list(item.get("benefits"),source,"benefits",True,quality_trace),"downsides":_list(item.get("downsides"),source,"downsides",True,quality_trace),"assumptions":_list(item.get("assumptions"),source,"assumptions",True),"conditions_for_success":_list(item.get("conditions_for_success"),source,"conditions_for_success",True,quality_trace),"evidence_ids":[]}
        alternatives.append(normalized)
    response["alternatives"]=alternatives
    recommendation=response.get("recommendation",{})
    recommendation["recommended_option"],option_rule=_clean_with_rule(recommendation.get("recommended_option"),source,optional=False,reject_instructions=False,reject_source_copy=True,field="recommended_option",trace=quality_trace)
    recommendation["rationale"],rationale_rule=_clean_with_rule(recommendation.get("rationale"),source,optional=False,reject_instructions=False,reject_source_copy=True,field="rationale",trace=quality_trace)
    recommendation["prerequisites"]=_list(recommendation.get("prerequisites"),source,"prerequisites",True)
    # One normalization authority: the nested recommendation collection is
    # canonical. The top-level compatibility field is projected only after
    # degradation, so removed items cannot survive through an alias.
    canonical_change_conditions=_list(recommendation.get("what_would_change_the_recommendation"),source,"recommendation_change_conditions",True,quality_trace)
    recommendation["what_would_change_the_recommendation"]=canonical_change_conditions
    response["problem_understanding"],problem_rule=_clean_with_rule(response.get("problem_understanding"),source,optional=False,reject_source_copy=True,field="problem_understanding",trace=quality_trace)
    unresolved=_list(response.get("unresolved_questions"),source,"unresolved_questions",True)
    unresolved,uncertainty_keys=_dedupe_uncertainties(unresolved,state)
    unknown,all_uncertainty_keys=_dedupe_uncertainties(_list(response.get("evidence_quality",{}).get("unknown",[]),source,"unknown",True),state,set(uncertainty_keys))
    response["evidence_quality"]={"known":response["key_facts"],"derived":response["derived_facts"],"assumed":_list(response.get("assumptions"),source,"assumptions",True),"unknown":unknown}
    response["assumptions"]=response["evidence_quality"]["assumed"]
    response["unresolved_questions"]=unresolved
    tensions=[]
    for item in response.get("goal_tensions",[]):
        tension=_clean(item.get("tension"),source)
        if tension and not re.search(r"^Balance\s+['\"]",tension): tensions.append(_semantic_structure({**item,"tension":tension},source))
    response["goal_tensions"]=tensions
    for key in ("resources","constraints","resource_risks","trends","causal_effects","confidence_rationale","what_changed"):
        response[key]=_semantic_structure(response.get(key,[]),source)
    required_failure=("recommended_option",option_rule) if not recommendation.get("recommended_option") else (("rationale",rationale_rule) if not recommendation.get("rationale") else (("problem_understanding",problem_rule) if not response.get("problem_understanding") else None))
    if required_failure:
        required_field,quality_rule=required_failure
        logger.warning("final_quality_stage=failed failure_category=malformed_required_section required_field=%s quality_rule=%s quality_action=hard_failure",required_field,quality_rule or "unknown")
        raise FinalBriefQualityError(["malformed_required_section"],required_field=required_field,quality_rule=quality_rule or "unknown")
    semantic_routing,semantic_candidates,semantic_triggers=route_semantic_ambiguity(response,quality_trace,generation_usage)
    semantic_usage={"invoked":False,"candidate_count":len(semantic_candidates),"triggers":semantic_triggers}
    if semantic_routing is SemanticRouting.AMBIGUOUS:
        trigger=semantic_triggers[0] if semantic_triggers else "none"
        if int(generation_usage.get("retry_count",0)):
            _semantic_event("skipped",trigger="call_budget_exhausted",action="skipped_call_budget")
            semantic_usage["stage"]="skipped_call_budget"
        elif callable(semantic_classifier):
            _semantic_event("started",trigger=trigger)
            payload=[{"field_id":item["field_id"],"item_index":item["item_index"],"text":item["text"]} for item in semantic_candidates]
            semantic_usage["payload_chars"]=len(str(payload));semantic_usage["invoked"]=True
            try:
                raw_semantic,classifier_usage=semantic_classifier(payload)
                results=_validate_semantic_results(raw_semantic,semantic_candidates);semantic_usage.update({key:classifier_usage.get(key) for key in ("latency_ms","input_tokens","output_tokens","total_tokens") if classifier_usage.get(key) is not None})
                removals=[];result_counts={result:0 for result in SEMANTIC_QUALITY_RESULTS}
                for candidate in semantic_candidates:
                    item=results[(candidate["field_id"],candidate["item_index"])]
                    result_counts[item["result"]]+=1
                    action="retained"
                    if item["result"]=="incomplete":
                        if candidate["optional"]:removals.append(candidate["path"]);action="degraded"
                        else:
                            _semantic_event("failed",field=candidate["field_id"],result="incomplete",action="safe_failure")
                            raise FinalBriefQualityError(["semantic_incomplete_required"],required_field=candidate["field_id"],quality_rule=item["reason"])
                    _semantic_event("passed",field=candidate["field_id"],result=item["result"],action=action)
                _remove_semantic_paths(response,removals);semantic_usage.update({"degraded_count":len(removals),"result_counts":result_counts,"stage":"passed"})
            except FinalBriefQualityError:raise
            except ProviderTimeoutError:
                _semantic_event("failed",failure="timeout",action="retained");semantic_usage["stage"]="timeout"
            except ProviderUnavailableError:
                _semantic_event("failed",failure="unavailable",action="retained");semantic_usage["stage"]="unavailable"
            except (InvalidModelResponseError,ValueError,TypeError,KeyError):
                _semantic_event("failed",failure="invalid_schema",action="retained");semantic_usage["stage"]="invalid_schema"
        else:
            semantic_usage["stage"]="unavailable"
    else:
        _semantic_event("skipped",trigger="none",action="none");semantic_usage["stage"]="skipped_complete"
    # Project compatibility aliases only after semantic decisions.
    canonical_change_conditions=recommendation.get("what_would_change_the_recommendation",[])
    response["what_would_change_recommendation"]=list(canonical_change_conditions)
    response["analysis"]=recommendation["rationale"]
    deliverables=response.get("requested_deliverables",{})
    horizon=deliverables.get("plan_horizon")
    if horizon:
        from app.intelligence_v2.quality import final_decision_plan
        response["decision_plan"]=final_decision_plan(horizon,recommendation=recommendation["recommended_option"],alternatives=alternatives,goals=response.get("goals",[]),gaps=state.information_gaps,change_conditions=recommendation["what_would_change_the_recommendation"])
        if plan_failure:=_final_semantic_failure({"decision_plan":response["decision_plan"]},source):
            required_field,quality_rule=plan_failure
            logger.warning("final_quality_stage=failed failure_category=malformed_final_response required_field=%s quality_rule=%s quality_action=hard_failure",required_field,quality_rule)
            raise FinalBriefQualityError(["malformed_final_response"],required_field=required_field,quality_rule=quality_rule)
    response["decision_plan"]=_plan(response.get("decision_plan",{}),source)
    gap_prose={gap.why_needed.lower() for gap in state.information_gaps if gap.can_proceed_without}
    response["uncertainties"],_= _dedupe_uncertainties([item for item in response["uncertainties"] if item.lower() not in gap_prose],state,set(all_uncertainty_keys))
    phases=response["decision_plan"].get("phases",[])
    response["next_move"]=phases[0].get("actions",[None])[0] if horizon and phases else (_clean(response.get("next_move"),source,reject_instructions=False) if not horizon else None)
    response["evidence_used"]=[];response["citations"]=[]
    plan=response.get("decision_plan",{})
    required_failure=None
    if deliverables.get("tradeoffs") and not any(item.get("benefits") or item.get("downsides") for item in alternatives):failures.append("missing_tradeoffs")
    if deliverables.get("assumptions") and not response["assumptions"]:failures.append("missing_assumptions")
    if deliverables.get("uncertainty") and not (unknown or unresolved):failures.append("missing_uncertainty")
    if deliverables.get("risks") and not response["risks"]:failures.append("missing_risks")
    if deliverables.get("ranking") and len(alternatives)<2:failures.append("missing_ranking")
    if deliverables.get("next_steps") and not response["prioritized_actions"]:failures.append("missing_next_steps")
    if deliverables.get("change_triggers") and not recommendation.get("what_would_change_the_recommendation"):failures.append("missing_change_conditions")
    if horizon and (not plan.get("phases") or plan.get("horizon_value")!=horizon.get("value") or plan.get("horizon_unit")!=horizon.get("unit") or any(not phase.get("actions") for phase in plan.get("phases",[]))):failures.append("missing_requested_plan")
    final_semantic_failure=_final_semantic_failure(response,source)
    if final_semantic_failure:
        required_failure=required_failure or final_semantic_failure;failures.append("malformed_final_response")
    elapsed=round((time.perf_counter()-started)*1000,3);response.setdefault("telemetry",{}).update({"final_quality_ms":elapsed,"semantic_quality":semantic_usage,"provider_calls":1+int(generation_usage.get("retry_count",0))+int(semantic_usage["invoked"])})
    response["completeness"].update({"recommendation":bool(recommendation.get("recommended_option") and recommendation.get("rationale")),"tradeoffs":not deliverables.get("tradeoffs") or bool(alternatives),"assumptions":not deliverables.get("assumptions") or bool(response["assumptions"]),"uncertainty":not deliverables.get("uncertainty") or bool(unknown or unresolved),"risks":not deliverables.get("risks") or bool(response["risks"]),"ranking":not deliverables.get("ranking") or len(alternatives)>=2,"next_steps":not deliverables.get("next_steps") or bool(response["prioritized_actions"]),"change_triggers":not deliverables.get("change_triggers") or bool(recommendation.get("what_would_change_the_recommendation")),"plan":not horizon or bool(plan.get("phases"))})
    if failures:
        required_field,quality_rule=required_failure or ("unknown","unknown")
        logger.warning("final_quality_stage=failed failure_category=%s required_field=%s quality_rule=%s quality_action=hard_failure",",".join(sorted(set(failures))),required_field,quality_rule or "unknown")
        raise FinalBriefQualityError(failures,required_field=required_field,quality_rule=quality_rule or "unknown")
    logger.warning("final_quality_stage=passed")
    return response
