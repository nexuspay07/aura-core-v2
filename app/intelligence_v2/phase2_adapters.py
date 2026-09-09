"""Side-effect-free adapters that normalize relevant legacy intelligence concepts."""
from __future__ import annotations
import re,time
from app.intelligence_v2.quality import decision_drivers, deterministic_plan, goal_tensions, normalize_goals, requested_deliverables, resource_ledger

class Phase2DecisionAdapters:
    def enrich(self,state):
        started=time.monotonic(); ledger=state.request.source_metadata.get("fact_ledger",{}); text=state.request.user_query
        goals=normalize_goals(text,self._split_goals(ledger.get("goals",[]))+self._goals(text))
        normalized_resources=resource_ledger(ledger.get("facts",[]),text);resources=normalized_resources["resources"]
        uncertainties=self._sentences(text,r"\b(?:may|might|uncertain|evaluating|risk|burnout|competitor)\b")
        risks=list(dict.fromkeys(ledger.get("risks",[])+self._sentences(text,r"\b(?:outage|technical debt|concentration|burnout|competitor)\b")))
        tensions=[]
        effects=[]
        lower=text.lower()
        if "technical debt" in lower: effects.append({"cause":"technical debt","effect":"increased outage and customer-retention risk","qualification":"may"})
        if "customer" in lower and ("concentration" in lower or "% of revenue" in lower): effects.append({"cause":"customer concentration","effect":"greater revenue and runway exposure if renewal is lost","qualification":"may"})
        if "burnout" in lower: effects.append({"cause":"sustained workload","effect":"reduced health and execution capacity","qualification":"may"})
        options=ledger.get("options",[]); options=options if len(options)>=2 else self._options(text)
        if not goals and options:
            goals=[f"evaluate {option}" for option in options]
        tensions=goal_tensions(goals,options)
        amounts={item["type"]:self._money(item["value"]) for item in [*normalized_resources["resources"],*normalized_resources["constraints"]] if self._money(item["value"]) is not None}
        feasible=not (amounts.get("budget") is not None and amounts.get("hiring_cost") is not None and amounts["hiring_cost"]>amounts["budget"])
        complex_decision=bool(len(goals)>1 or len(resources)>=3 or len(options)>=2 or uncertainties or re.search(r"\b(?:should|decide|choose|allocate|trade-?off)\b",lower))
        participation={"context":True,"memory":bool(state.request.memory_context),"world_model":complex_decision,"goals":bool(goals),"multi_goal":len(goals)>1,"resource":bool(resources),"uncertainty":bool(uncertainties),"causal":bool(effects),"strategy":len(options)>1,"planning":complex_decision,"goal_task":complex_decision,"self_evaluation":complex_decision,"learning":False,"rl":False}
        deliverables=requested_deliverables(text);plan=deterministic_plan(deliverables["plan_horizon"],normalized_resources,uncertainties) or {"style":"prioritized_actions"}
        plan["feasible"]=feasible
        state.request.source_metadata["requested_deliverables"]=deliverables
        state.analysis_outputs["phase2"]={"world_state":{"facts":ledger.get("facts",[]),"constraints":state.request.constraints,"relationships":effects},"goals":goals,"competing_goals":goals if len(goals)>1 else [],"goal_tensions":tensions,"resources":resources,"constraints":normalized_resources["constraints"],"resource_risks":normalized_resources["risks"],"trends":normalized_resources["trends"],"decision_drivers":decision_drivers(normalized_resources),"uncertainties":uncertainties,"options":options,"tradeoffs":[{"option":option,"assessment":"compare against stated goals, resources, and risks"} for option in options],"causal_effects":effects,"risks":list(dict.fromkeys(risks+[item["value"] for item in normalized_resources["risks"]])),"plan":plan,"requested_deliverables":deliverables,"revision_reason":list(state.request.source_metadata.get("authoritative_user_constraints",{}).values()),"self_evaluation":{"requires_grounding":True,"resource_feasible":feasible,"has_change_triggers":True},"participation":participation}
        if state.analysis_status=="READY_FOR_ANALYSIS":
            state.selected_tools.extend(k for k,v in participation.items() if v and k not in state.selected_tools)
        state.request.source_metadata.setdefault("timings_ms",{})["phase2_enrichment_ms"]=round((time.monotonic()-started)*1000,3)
        return state
    @staticmethod
    def _sentences(text,pattern): return [s.strip() for s in re.split(r"[.;]\s*",text) if re.search(pattern,s,re.I)][:6]
    @staticmethod
    def _goals(text):
        match=re.search(r"\bgoals?\s*(?:are|include|:)?\s*([^.;]+)",text,re.I)
        return [v.strip() for v in re.split(r",|\band\b",match.group(1)) if v.strip()] if match else []
    @staticmethod
    def _split_goals(goals):
        return [part.strip() for goal in goals for part in re.split(r"\bwhile\b|\band\b",goal,flags=re.I) if part.strip()]
    @staticmethod
    def _options(text):
        numbered=[value.strip() for value in re.findall(r"(?:^|\n)\s*\d+[.)]\s*([^\n]+)",text)]
        if len(numbered)>=2:return numbered[:6]
        match=re.search(r"\b(?:should (?:i|we)|choose between)\s+([^?]+)",text,re.I)
        if match:return [v.strip() for v in re.split(r",|\bor\b",match.group(1)) if v.strip()]
        return list(dict.fromkeys(re.findall(r"\bOffer\s+[A-Z]\b",text,re.I)))
    @staticmethod
    def _money(value):
        match=re.search(r"\$\s*([\d,.]+)\s*([km]?)",str(value),re.I)
        if not match:return None
        return float(match.group(1).replace(",",""))*({"k":1000,"m":1000000}.get(match.group(2).lower(),1))

phase2_decision_adapters=Phase2DecisionAdapters()
