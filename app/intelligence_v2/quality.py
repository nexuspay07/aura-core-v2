"""Deterministic normalization and completeness policy for decision briefs."""
from __future__ import annotations

import re
from typing import Any


def requested_deliverables(text: str) -> dict[str, Any]:
    lower = text.lower()
    plan = re.search(r"\b(\d+)[- ](day|month)s?\s+(?:action\s+|practical\s+)?plan\b", lower)
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


def goal_tensions(goals: list[str], options: list[str]) -> list[dict[str, Any]]:
    return [{"goal_a": left, "goal_b": right, "tension": f"Balance '{left}' with '{right}'", "affected_options": options[:4]} for left, right in zip(goals, goals[1:]) if left.lower() != right.lower()]


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


def deterministic_plan(horizon: dict[str, Any] | None, ledger: dict[str, list[dict]], uncertainties: list[str]) -> dict[str, Any]:
    if horizon is None: return {}
    verify = [f"Verify {item['type'].replace('_',' ')} before making an irreversible commitment" for item in ledger["risks"][:2]]
    phases = [
        {"phase":"Early phase","objective":"Confirm decision-critical unknowns","actions":verify or ["Confirm the terms and constraints that differ across the options"],"checkpoint":"Record confirmed terms separately from uncertain possibilities","dependencies":[],"reassessment_trigger":uncertainties[0] if uncertainties else "Material new evidence changes option feasibility"},
        {"phase":"Middle phase","objective":"Test the most reversible viable path","actions":["Run the smallest reversible test supported by the available resources"],"checkpoint":"Compare observed effects with the stated goals and constraints","dependencies":["Early-phase facts are confirmed"],"reassessment_trigger":"The test materially worsens runway, capacity, or risk"},
        {"phase":"Final phase","objective":"Reassess and commit deliberately","actions":["Update the decision using confirmed evidence and the observed test result"],"checkpoint":"Document the selected option and evidence that would reverse it","dependencies":["The reversible test has usable results"],"reassessment_trigger":"A recommendation-change condition is met"},
    ]
    value,unit=horizon["value"],horizon["unit"]
    return {"style":"phased","horizon_value":value,"horizon_unit":unit,"horizon_label":f"{value}-{unit[:-1].title()}",**({"horizon_days":value} if unit=="days" else {}),"basis":"explicitly requested horizon","phases":phases}


def evidence_quality(known: list[str], derived: list[str], assumed: list[str], unknown: list[str]) -> dict[str, list[str]]:
    unique=lambda items:list(dict.fromkeys(item for item in items if item))
    return {"known":unique(known),"derived":unique(derived),"assumed":unique(assumed),"unknown":unique(unknown)}
