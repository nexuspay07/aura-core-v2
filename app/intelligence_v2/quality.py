"""Deterministic normalization and completeness policy for decision briefs."""
from __future__ import annotations

import re
from typing import Any


def requested_deliverables(text: str) -> dict[str, Any]:
    lower = text.lower()
    plan = re.search(r"\b(\d+)[- ](day|month)s?\s+(?:action\s+|practical\s+)?plan\b", lower)
    if not plan:
        plan = re.search(r"\b(?:plan|roadmap)\b[^.!?]{0,50}?\b(?:for|over|across)\s+(?:the\s+)?(?:next\s+)?(\d+)\s+(day|month)s?\b",lower)
    horizon={"value":int(plan.group(1)),"unit":f"{plan.group(2)}s"} if plan else None
    return {
        "recommendation": bool(re.search(r"\brecommend(?:ation|ed)?\b|what should (?:i|we) do", lower)),
        "tradeoffs": bool(re.search(r"\btrade[- ]?offs?\b|pros? and cons?|compar(?:e|ison)", lower)),
        "assumptions": "assumption" in lower,
        "uncertainty": bool(re.search(r"\buncertaint(?:y|ies)\b", lower)),
        "risks": bool(re.search(r"\brisks?\b", lower)),
        "ranking": bool(re.search(r"\brank(?:ing)?\b", lower)),
        "next_steps": bool(re.search(r"\bnext steps?\b", lower)),
        "change_triggers": bool(re.search(r"\b(?:what|developments?).{0,50}\bchange (?:your|the) recommendation\b", lower)),
        "plan_days": horizon["value"] if horizon and horizon["unit"]=="days" else None,
        "plan_horizon": horizon,
    }


def _clean_goal(value: str) -> str:
    value = re.sub(r"^\s*(?:my|our)\s+(?:long[- ]term\s+)?goal\s+(?:is|:)?\s*", "", value, flags=re.I)
    value = re.sub(r"^\s*(?:is\s+|to\s+)", "", value, flags=re.I)
    value = re.sub(r"^\s*but\s+", "", value, flags=re.I)
    value = re.sub(r"\s+", " ", value).strip(" ,.;")
    if re.match(r"i (?:do not|don't) want to ", value, re.I):
        value = re.sub(r"^i (?:do not|don't) want to ", "Avoid ", value, flags=re.I)
    return value[:1].upper() + value[1:] if value else ""


def normalize_goals(text: str, extracted: list[str]) -> list[str]:
    candidates: list[str] = []
    for value in extracted:
        candidates.extend(re.split(r"\b(?:but|while)\b", value, flags=re.I))
    if re.search(r"\bburn(?:ed|t)?\s*out\b|\bburnout\b", text, re.I):
        candidates.append("Reduce the explicitly stated unsustainable workload and burnout")
    normalized: list[str] = []
    token_sets: list[set[str]] = []
    for candidate in candidates:
        goal = _clean_goal(candidate)
        if not goal:
            continue
        if re.search(r"\b(?:i|we)\s+(?:do not|don't)$", goal, re.I):
            continue
        goal = re.sub(r"^Avoid put\b", "Avoid putting", goal, flags=re.I)
        if len(goal.split()) == 1:
            goal = f"Prioritize {goal.lower()}"
        tokens = set(re.findall(r"[a-z0-9]+", goal.lower())) - {"i", "my", "the", "a", "to", "is"}
        if any(tokens <= prior or prior <= tokens or len(tokens & prior) / max(1, min(len(tokens), len(prior))) >= .8 for prior in token_sets):
            continue
        normalized.append(goal); token_sets.append(tokens)
    return normalized[:6]


_TENSION_AXES = (
    (r"\b(?:preserve|protect|security|stability|safe|reserve|health|wellbeing)\b", r"\b(?:grow|build|expand|start|change|transition|pursue|increase)\b", "Protect stability while pursuing progress"),
    (r"\b(?:learn|education|knowledge|explore|breadth|depth)\b", r"\b(?:earn|income|workforce|career|build|execute|launch|experience)\b", "Balance learning and exploration with execution and near-term progress"),
    (r"\b(?:quick|soon|speed|rapid|immediate)\b", r"\b(?:quality|durable|sustainable|careful|reliable)\b", "Balance speed with durability and quality"),
    (r"\b(?:health|wellbeing|capacity|burnout|time)\b", r"\b(?:workload|growth|expand|build|launch)\b", "Balance sustainable capacity with the desired level of progress"),
)


def goal_tensions(goals: list[str], options: list[str]) -> list[dict[str, Any]]:
    tensions=[];seen=set()
    for index,left in enumerate(goals):
        for right in goals[index+1:]:
            semantic_left=re.sub(r"\bbuild\s+(?:durable\s+)?(?:skills?|knowledge|capabilit(?:y|ies))\b","learn",left,flags=re.I)
            semantic_right=re.sub(r"\bbuild\s+(?:durable\s+)?(?:skills?|knowledge|capabilit(?:y|ies))\b","learn",right,flags=re.I)
            description=next((label for first,second,label in _TENSION_AXES if (re.search(first,semantic_left,re.I) and re.search(second,semantic_right,re.I)) or (re.search(second,semantic_left,re.I) and re.search(first,semantic_right,re.I))),None)
            if not description or description in seen: continue
            seen.add(description)
            tensions.append({"goal_a":left,"goal_b":right,"tension":description,"affected_options":options[:4]})
    return tensions[:4]


def resource_ledger(facts: list[dict], text: str) -> dict[str, list[dict]]:
    buckets = {"resources": [], "constraints": [], "risks": [], "trends": []}
    mapping = {"salary":("resources","financial"),"savings":("resources","financial"),"cash":("resources","financial"),"budget":("resources","financial"),"runway":("resources","financial"),"revenue":("resources","business"),"mrr":("resources","business"),"customer_count":("resources","business"),"team_size":("resources","business"),"workload":("constraints","time"),"expenses":("constraints","financial"),"debt":("constraints","financial"),"interest_rate":("constraints","financial"),"hiring_cost":("constraints","financial"),"deadline":("constraints","time"),"renewal_deadline":("constraints","time"),"customer_concentration":("risks","business"),"growth_rate":("trends","business"),"expense_change":("risks","financial")}
    seen = set()
    for fact in facts:
        destination = mapping.get(fact.get("type")); key = (fact.get("type"), fact.get("value"))
        if not destination or key in seen: continue
        seen.add(key); bucket, category = destination
        buckets[bucket].append({"type":fact["type"],"value":fact["value"],"category":category,"basis":"known"})
    if re.search(r"\bburn(?:ed|t)?\s*out\b|\bburnout\b", text, re.I): buckets["constraints"].append({"type":"personal_capacity","value":"Explicitly stated burnout","category":"personal_capacity","basis":"known"})
    if re.search(r"\bnothing is signed\b", text, re.I): buckets["risks"].append({"type":"unsigned_expansion","value":"Potential expansion is unsigned","category":"business","basis":"known"})
    return buckets


def decision_drivers(ledger: dict[str, list[dict]]) -> list[str]:
    priority = [*ledger["risks"], *ledger["constraints"], *ledger["trends"], *ledger["resources"]]
    return [f"{item['type'].replace('_',' ')}: {item['value']}" for item in priority[:7]]


def deterministic_plan(horizon: dict[str, Any] | None, ledger: dict[str, list[dict]], uncertainties: list[str], options: list[str] | None = None, goals: list[str] | None = None) -> dict[str, Any]:
    if horizon is None: return {}
    options=[item for item in (options or []) if item][:3];goals=[item for item in (goals or []) if item][:2]
    option_summary=" and ".join(options[:2]) or "the viable options"
    goal_summary=" and ".join(goals[:2]) or "the stated goals and constraints"
    unknowns=[re.sub(r"^[a-z][a-z0-9_]+:\s*","",item,flags=re.I).strip() for item in uncertainties if item][:2]
    verify=[f"Clarify {item[:1].lower()+item[1:]}" for item in unknowns]
    if not verify: verify=[f"Compare {option_summary} against {goal_summary}"]
    phases = [
        {"phase":"Early phase","objective":"Confirm decision-critical unknowns","actions":verify,"checkpoint":f"Record what is confirmed about {option_summary}","dependencies":[],"reassessment_trigger":unknowns[0] if unknowns else "Material new evidence changes option feasibility"},
        {"phase":"Middle phase","objective":f"Test the most reversible path involving {options[0] if options else 'the leading option'}","actions":[f"Test {options[0] if options else 'the leading option'} through one reversible next step tied to {goals[0] if goals else 'the primary goal'}"],"checkpoint":f"Compare the observed result against {goal_summary}","dependencies":["Decision-critical facts are confirmed"],"reassessment_trigger":"The test materially worsens a stated resource, capacity, or risk constraint"},
        {"phase":"Final phase","objective":"Choose using confirmed evidence","actions":[f"Choose between {option_summary} using the confirmed results and {goal_summary}"],"checkpoint":"Document the selected option and the evidence that would reverse it","dependencies":["The reversible test produced usable evidence"],"reassessment_trigger":"A recommendation-change condition is met"},
    ]
    value,unit=horizon["value"],horizon["unit"]
    return {"style":"phased","horizon_value":value,"horizon_unit":unit,"horizon_label":f"{value}-{unit[:-1].title()}",**({"horizon_days":value} if unit=="days" else {}),"basis":"explicitly requested horizon","phases":phases}


def evidence_quality(known: list[str], derived: list[str], assumed: list[str], unknown: list[str]) -> dict[str, list[str]]:
    unique=lambda items:list(dict.fromkeys(item for item in items if item))
    return {"known":unique(known),"derived":unique(derived),"assumed":unique(assumed),"unknown":unique(unknown)}


def _time_windows(horizon: dict[str, Any]) -> list[str]:
    value,unit=horizon["value"],horizon["unit"]
    count=4 if unit=="months" and value>=8 else 3
    windows=[]
    for index in range(count):
        start=(index*value)//count+1;end=((index+1)*value)//count
        label="Months" if unit=="months" else "Days"
        windows.append(f"{label} {start}–{end}" if start!=end else f"{label[:-1]} {start}")
    return windows


def final_decision_plan(horizon: dict[str, Any] | None, *, recommendation: str, alternatives: list[dict], goals: list[str], gaps: list[Any], change_conditions: list[str]) -> dict[str, Any]:
    """Build a display-ready plan after grounded provider analysis."""
    if not horizon:return {}
    windows=_time_windows(horizon);options=[item.get("option") for item in alternatives if item.get("option")]
    selected=recommendation.strip();primary_goal=goals[0] if goals else "the stated decision goal"
    question=next((gap.suggested_question.rstrip(" ?") for gap in gaps if gap.can_proceed_without),None)
    reassess=next(iter(change_conditions),None) or next((gap.impact_on_decision for gap in gaps if gap.can_proceed_without),"Material new evidence changes the recommendation")
    first_action=f"Gather the information needed to answer: {question}" if question else f"Confirm the constraints that materially distinguish {' and '.join(options[:2]) or selected}"
    blueprints=[
        ("Confirm the decision basis",first_action,"Record confirmed facts separately from remaining uncertainty"),
        ("Test the recommendation reversibly",f"Take one reversible step toward {selected}",f"Document what the step reveals about {primary_goal}"),
        ("Compare evidence with the decision goals",f"Compare the observed result with {primary_goal}","Identify which option is best supported by the observed evidence"),
        ("Make the next commitment",f"Commit further to {selected} only if the checkpoint evidence supports it","Record the decision and the evidence that would reverse it"),
    ]
    if len(windows)==3:blueprints=[blueprints[0],blueprints[1],blueprints[3]]
    phases=[{"phase":window,"objective":objective,"actions":[action],"checkpoint":checkpoint,"dependencies":[] if index==0 else ["The previous checkpoint is complete"],"reassessment_trigger":reassess} for index,(window,(objective,action,checkpoint)) in enumerate(zip(windows,blueprints))]
    value,unit=horizon["value"],horizon["unit"]
    return {"style":"phased","horizon_value":value,"horizon_unit":unit,"horizon_label":f"{value}-{unit[:-1].title()}",**({"horizon_days":value} if unit=="days" else {}),"basis":"explicitly requested horizon","phases":phases}
