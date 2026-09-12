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

_OPTION_VERB=re.compile(r"^(?:accept|build|buy|choose|defer|delay|enter|finish|keep|launch|leave|pursue|remain|return|sell|start|stay|study|take|wait|work)\b",re.I)

def _extract_options(text):
    header=re.search(r"\b(?:(?P<count>two|three|four|2|3|4)\s+)?(?:paths?|options?|choices?)\s*(?:is|are|include|:)?\s*",text,re.I)
    either=re.search(r"\beither\s+",text,re.I)
    marker=header or either
    if not marker:return []
    tail=text[marker.end():][:800].strip()
    numbered=[item.strip(" \t\r\n-•.;") for item in re.findall(r"(?:^|[.;]\s*)\d+[.)]\s*(.+?)(?=(?:[.;]\s*)\d+[.)]|$)",tail,re.S)]
    if len(numbered)>=2:return numbered[:4]
    bullets=[line.strip(" \t-•") for line in tail.splitlines() if re.match(r"^\s*[-•]\s+",line)]
    if len(bullets)>=2:return bullets[:4]
    count_words={"two":2,"three":3,"four":4,"2":2,"3":3,"4":4};count=count_words.get(header.group("count").lower()) if header and header.group("count") else None
    if count:
        sentences=[item.strip(" .") for item in re.split(r"\.\s+",tail) if item.strip()]
        if len(sentences)>=count:return sentences[:count]
    first_sentence=re.split(r"[.\n]",tail,1)[0].strip()
    semicolon=[item.strip() for item in first_sentence.split(";") if item.strip()]
    if len(semicolon)>=2:return semicolon[:4]
    comma=[re.sub(r"^\s*(?:and|or)\s+","",item.strip(),flags=re.I) for item in first_sentence.split(",") if item.strip()]
    if len(comma)>=2:return comma[:4]
    if re.search(r"\bor\b",first_sentence,re.I):
        left,right=(item.strip() for item in re.split(r"\bor\b",first_sentence,maxsplit=1,flags=re.I))
        explicit_pair=bool(either or count==2 or (_OPTION_VERB.search(left) and _OPTION_VERB.search(right)))
        if explicit_pair:return [left,right]
    return [first_sentence] if first_sentence else []

def extract_fact_ledger(text):
    original=text
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
    options=_extract_options(original)
    if not options:
        match=re.search(r"\b(?:i(?:'m| am)|we(?:'re| are))\s+deciding\s+between\s+([^.;\n?]+)",text,re.I)
        if match:
            left,right=(item.strip() for item in re.split(r"\band\b|\bor\b",match.group(1),maxsplit=1,flags=re.I))
            options=[left,right] if left and right else []
    risks=[m.group(0).strip() for m in re.finditer(r"[^.;\n]{0,50}\b(?:risk|burnout|outage|competitor|concentration|churn)\b[^.;\n]{0,70}",text,re.I)]
    return {"facts":facts,"goals":goals,"options":options,"risks":risks}

def has_fact(ledger,*types): return bool({f["type"] for f in ledger["facts"]}&set(types))
def is_business_scenario(text,ledger):
    signals={f["type"] for f in ledger["facts"]}&{"revenue","mrr","cash","team_size","customer_count","customer_concentration","hiring_cost"}
    return len(signals)>=2 or bool(signals and re.search(r"\b(?:our|company|business|startup|customers?|engineers?|MRR|ARR)\b",text,re.I))
