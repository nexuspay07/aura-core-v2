"""Conservative deterministic fact ledger used before clarification."""
import re

MONEY=r"\$\s*[\d,]+(?:\.\d+)?\s*(?:k|m)?"
PATTERNS={
"salary":rf"\b(?:salary|employment income|earn(?:ing|s)?)\b[^\n.;]{{0,30}}?({MONEY})",
"revenue":rf"\b(?:monthly\s+revenue|revenue)\b[^\n.;]{{0,24}}?({MONEY})",
"mrr":rf"\b(?:MRR|monthly recurring revenue)\b[^\n.;]{{0,24}}?({MONEY})|({MONEY})\s*(?:in\s+)?(?:MRR|monthly recurring revenue)\b",
"expenses":rf"\b(?:monthly\s+)?expenses?\b[^\n.;]{{0,24}}?({MONEY})|({MONEY})\s*(?:monthly\s+)?expenses?\b",
"savings":rf"({MONEY})\s*(?:in\s+)?savings\b|\bsavings\b[^\n.;]{{0,20}}?({MONEY})","debt":rf"({MONEY})\s*(?:in\s+)?(?:student\s+)?debt\b",
"interest_rate":r"\b(?:interest(?:\s+rate)?|loan(?:\s+interest)?(?:\s+rate)?)\b[^\n.;]{0,20}?(\d+(?:\.\d+)?\s*%)|\b(\d+(?:\.\d+)?\s*%)\s*(?:student\s+)?loan\b",
"cash":rf"({MONEY})\s*(?:in\s+)?cash\b|\b(?:available\s+)?cash\b[^\n.;]{{0,20}}?({MONEY})",
"runway":r"\b(\d+(?:\.\d+)?\s*(?:days?|weeks?|months?|years?))\s+(?:of\s+)?runway\b",
"housing_cost":rf"\b(?:rent|housing cost)\b[^\n.;]{{0,20}}?({MONEY})",
"growth_rate":r"(\d+(?:\.\d+)?\s*%)\s*(?:(?:monthly\s+)?growth|per\s+month)","customer_count":r"\b(\d+)\s+(?:paying\s+)?customers?\b",
"customer_concentration":r"(\d+(?:\.\d+)?\s*%)\s*(?:top[- ]?\d+|largest[- ]customer|customer concentration)|\b(?:top[- ]?\d+|largest[- ]customer|customer concentration|(?:two|three|four|\d+)\s+customers?\s+(?:account|represent))\b[^\n.;]{0,40}?(\d+(?:\.\d+)?\s*%)",
"renewal_deadline":r"\b(?:contract\s+)?renew(?:al|s?)\b[^\n.;]{0,20}?(\d+\s*(?:days?|weeks?|months?))|\b(\d+\s*(?:days?|weeks?|months?))\s+(?:until|to)\s+(?:contract\s+)?renewal\b",
"workload":r"\b(\d+(?:\.\d+)?\s*(?:h|hours?)\s*(?:/|per\s*|a\s+)?week)\b","team_size":r"\b(\d+)[- ]person\b[^\n.;]{0,30}\b(?:team|company)\b",
"hiring_cost":rf"\b(?:hire|engineers?|staff)\b[^\n.;]{{0,40}}?({MONEY})","deadline":r"\b(\d+\s*(?:days?|weeks?|months?|years?))\s+(?:to|until)|\b(?:within|deadline(?: is)?|in)\s+(\d+\s*(?:days?|weeks?|months?|years?))",
"budget":rf"\bbudget\b[^\n.;]{{0,20}}?({MONEY})|({MONEY})\s+budget\b",
"expense_change":r"\b(?:rent|expense|cost)\b[^\n.;]{0,40}?\b(?:increase|rise|grow)\b[^\n.;]{0,20}?(\d+(?:\.\d+)?\s*%)|\b(\d+(?:\.\d+)?\s*%)\b[^\n.;]{0,20}?\b(?:rent|expense|cost)\b[^\n.;]{0,20}?\b(?:increase|rise)\b"}

def extract_fact_ledger(text):
    text=re.sub(r"\s+"," ",text)
    facts=[]
    for kind,pattern in PATTERNS.items():
        for match in re.finditer(pattern,text,re.I):
            value=next((v for v in match.groups() if v),match.group(0));facts.append({"type":kind,"value":" ".join(value.split()),"source":"user_statement"})
    qualitative={
        "age":r"\b(?:i am|i'm)\s+(\d{1,2})(?:\s+years?\s+old)?\b",
        "current_status":r"\b(?:i am|i'm)?\s*(currently\s+(?:studying|working|employed|unemployed)[^.;]{0,55})",
        "resource_constraint":r"\b((?:my|our|i have|we have)\s+(?:very\s+)?limited\s+(?:financial\s+)?resources)\b",
        "time_constraint":r"\b((?:my|our|i have|we have)\s+(?:available\s+)?time\s+(?:is\s+)?(?:very\s+)?limited|time is (?:a\s+)?(?:material|major|significant) constraint)\b",
        "stated_value":r"\b((?:education|financial security|stability|health|family|independence|optionality)\s+(?:genuinely\s+|really\s+)?(?:matters|is important)(?:\s+to me|\s+to us)?)\b",
    }
    for kind,pattern in qualitative.items():
        for match in re.finditer(pattern,text,re.I):
            value=match.group(1).strip();normalized=f"{value} years old" if kind=="age" and "year" not in value.lower() else value
            facts.append({"type":kind,"value":normalized,"source":"user_statement"})
    goals=[next(v.strip() for v in m.groups() if v) for m in re.finditer(r"\b(?:my|our)\s+(?:long[- ]term\s+)?goal\s+(?:is|:)?\s*([^.;\n]+)|\b(?:i|we)\s+want\s+to\s+([^.;\n]+)",text,re.I)]
    options=[];match=re.search(r"\b(?:(?:three|four|3|4)\s+)?(?:paths?|options?|choices?)\s*(?:are|include|:)?\s*([^.;\n]+)",text,re.I)
    if not match: match=re.search(r"\b(?:i(?:'m| am)|we(?:'re| are))\s+deciding\s+between\s+([^.;\n?]+)",text,re.I)
    if match: options=[re.sub(r"^\s*(?:and\s+)?","",v.strip(),flags=re.I) for v in re.split(r",|\bor\b|/",match.group(1)) if v.strip()]
    risks=[m.group(0).strip() for m in re.finditer(r"[^.;\n]{0,50}\b(?:risk|burnout|outage|competitor|concentration|churn)\b[^.;\n]{0,70}",text,re.I)]
    return {"facts":facts,"goals":goals,"options":options,"risks":risks}

def has_fact(ledger,*types): return bool({f["type"] for f in ledger["facts"]}&set(types))
def is_business_scenario(text,ledger):
    signals={f["type"] for f in ledger["facts"]}&{"revenue","mrr","cash","team_size","customer_count","customer_concentration","hiring_cost"}
    return len(signals)>=2 or bool(signals and re.search(r"\b(?:our|company|business|startup|customers?|engineers?|MRR|ARR)\b",text,re.I))
