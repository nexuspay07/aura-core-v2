"""Side-effect-free adapters that normalize relevant legacy intelligence concepts."""
from __future__ import annotations
import re,time

class Phase2DecisionAdapters:
    def enrich(self,state):
        started=time.monotonic(); ledger=state.request.source_metadata.get("fact_ledger",{}); text=state.request.user_query
        goals=list(dict.fromkeys(self._split_goals(ledger.get("goals",[]))+self._goals(text)))
        resources=[f for f in ledger.get("facts",[]) if f["type"] in {"salary","revenue","mrr","expenses","savings","debt","cash","runway","workload","team_size","hiring_cost","budget","deadline"}]
        uncertainties=self._sentences(text,r"\b(?:may|might|uncertain|evaluating|risk|burnout|competitor)\b")
        risks=list(dict.fromkeys(ledger.get("risks",[])+self._sentences(text,r"\b(?:outage|technical debt|concentration|burnout|competitor)\b")))
        tensions=[]
        if len(goals)>1:
            for left,right in zip(goals,goals[1:]): tensions.append({"between":[left,right],"kind":"competing priorities"})
        effects=[]
        lower=text.lower()
        if "technical debt" in lower: effects.append({"cause":"technical debt","effect":"increased outage and customer-retention risk","qualification":"may"})
        if "customer" in lower and ("concentration" in lower or "% of revenue" in lower): effects.append({"cause":"customer concentration","effect":"greater revenue and runway exposure if renewal is lost","qualification":"may"})
        if "burnout" in lower: effects.append({"cause":"sustained workload","effect":"reduced health and execution capacity","qualification":"may"})
        options=ledger.get("options",[]) or self._options(text)
        if not goals and options:
            goals=[f"evaluate {option}" for option in options]
            tensions=[{"between":[left,right],"kind":"competing priorities"} for left,right in zip(goals,goals[1:])]
        amounts={item["type"]:self._money(item["value"]) for item in resources if self._money(item["value"]) is not None}
        feasible=not (amounts.get("budget") is not None and amounts.get("hiring_cost") is not None and amounts["hiring_cost"]>amounts["budget"])
        complex_decision=bool(len(goals)>1 or len(resources)>=3 or len(options)>=2 or uncertainties or re.search(r"\b(?:should|decide|choose|allocate|trade-?off)\b",lower))
        participation={"context":True,"memory":bool(state.request.memory_context),"world_model":complex_decision,"goals":bool(goals),"multi_goal":len(goals)>1,"resource":bool(resources),"uncertainty":bool(uncertainties),"causal":bool(effects),"strategy":len(options)>1,"planning":complex_decision,"goal_task":complex_decision,"self_evaluation":complex_decision,"learning":False,"rl":False}
        state.analysis_outputs["phase2"]={"world_state":{"facts":ledger.get("facts",[]),"constraints":state.request.constraints,"relationships":effects},"goals":goals,"competing_goals":goals if len(goals)>1 else [],"goal_tensions":tensions,"resources":resources,"uncertainties":uncertainties,"options":options,"tradeoffs":[{"option":option,"assessment":"compare against stated goals, resources, and risks"} for option in options],"causal_effects":effects,"risks":risks,"plan":{"style":"milestone" if re.search(r"\b(?:90 days|plan|allocate)\b",lower) else "prioritized_actions","milestones":["immediate","midpoint","by the stated deadline"],"feasible":feasible,"constraint":"Use only supplied numeric milestones."},"revision_reason":list(state.request.source_metadata.get("authoritative_user_constraints",{}).values()),"self_evaluation":{"requires_grounding":True,"resource_feasible":feasible,"has_change_triggers":True},"participation":participation}
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
        match=re.search(r"\b(?:should (?:i|we)|choose between)\s+([^?]+)",text,re.I)
        if match:return [v.strip() for v in re.split(r",|\bor\b",match.group(1)) if v.strip()]
        return list(dict.fromkeys(re.findall(r"\bOffer\s+[A-Z]\b",text,re.I)))
    @staticmethod
    def _money(value):
        match=re.search(r"\$\s*([\d,.]+)\s*([km]?)",str(value),re.I)
        if not match:return None
        return float(match.group(1).replace(",",""))*({"k":1000,"m":1000000}.get(match.group(2).lower(),1))

phase2_decision_adapters=Phase2DecisionAdapters()
