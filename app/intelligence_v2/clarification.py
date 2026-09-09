"""Deterministic information sufficiency and clarification for V2."""
from __future__ import annotations
from datetime import datetime, timezone
import re

from app.intelligence_v2.contracts import (AssumptionItem, AssumptionStatus, ClarificationPlan, ClarificationState, DecisionRequest, EvidenceConflict, EvidenceItem, EvidenceSourceType, GapImportance, GapPriority, InformationGap, InformationSufficiencyAssessment, ProceedDecision, SufficiencyStatus)

class StructuredAnswerExtractor:
    """Conservative extraction: unrecognised answers remain raw user evidence."""
    def extract(self, *, question: str, answer: str, request: DecisionRequest, turn: int) -> EvidenceItem:
        field = next((gap.field for gap in request.missing_information if gap.suggested_question == question), "unconfirmed")
        value=None; unit=None; confirmed=False
        if field == "current_cost_baseline":
            match=re.search(r"\$\s*(\d+(?:\.\d+)?)\s*(?:per|/)\s*(?:order|delivery)",answer,re.I)
            if match: value=match.group(1);unit="USD/order";confirmed=True
        elif field == "service_level_baseline":
            match=re.search(r"\b(\d+(?:\.\d+)?)\s*%",answer)
            if match: value=match.group(1);unit="percent";confirmed=True
        return EvidenceItem(id=f"clarification:{turn}:{len(request.known_facts)}",source_type=EvidenceSourceType.USER_STATEMENT,source_name="clarification_answer",content=answer,structured_value={"topic":field,"value":value,"unit":unit,"confirmed":confirmed},organization_id=request.organization_id,workspace_id=request.workspace_id,timestamp=datetime.now(timezone.utc),permission_scope="session",citation_label="User clarification",provenance={"session_id":request.session_id,"turn":turn,"raw_statement":answer,"confirmation_status":"confirmed" if confirmed else "unconfirmed","memory_promotion":"candidate" if confirmed and field in {"current_cost_baseline","service_level_baseline"} else "session_only"})

class InformationSufficiencyService:
    max_questions=1
    def assess(self, *, request: DecisionRequest, gaps: list[InformationGap], conflicts: list[EvidenceConflict]) -> InformationSufficiencyAssessment:
        coverage={gap.field:False for gap in gaps}
        # Gaps are absent only after authorized evidence has answered them.
        for gap in request.missing_information:
            coverage[gap.field]=False
        critical=[gap for gap in gaps if not gap.can_proceed_without]; important=[gap for gap in gaps if gap.can_proceed_without and gap.importance in {GapImportance.CRITICAL,GapImportance.HIGH}]; optional=[gap for gap in gaps if gap.can_proceed_without and gap.importance in {GapImportance.MEDIUM,GapImportance.LOW}]
        if conflicts: status=SufficiencyStatus.CONTRADICTORY; can=False; action="Clarify conflicting evidence before analysis."
        elif critical: status=SufficiencyStatus.INSUFFICIENT; can=False; action="Ask the highest-value clarification questions."
        elif important: status=SufficiencyStatus.PARTIALLY_SUFFICIENT; can=True; action="Proceed cautiously or clarify important uncertainty."
        else: status=SufficiencyStatus.SUFFICIENT; can=True; action="Ready for analysis."
        return InformationSufficiencyAssessment(status,coverage,critical,important,optional,conflicts,[gap.field for gap in critical],can,action,["Evidence coverage maps only required fields: true means authorized evidence satisfied the requirement."])
    def prioritize(self, gaps:list[InformationGap]) -> list[GapPriority]:
        base={GapImportance.CRITICAL:100,GapImportance.HIGH:70,GapImportance.MEDIUM:40,GapImportance.LOW:20}
        result=[]
        for gap in gaps:
            score=base[gap.importance]+(20 if not gap.can_proceed_without else 0)
            result.append(GapPriority(gap,score,["decision impact", "blocking" if not gap.can_proceed_without else "can proceed without it", "user burden kept concise"]))
        return sorted(result,key=lambda item:(-item.score,item.gap.field))

class ClarificationPlanner:
    def plan(self, *, request:DecisionRequest, assessment:InformationSufficiencyAssessment, state:ClarificationState) -> ClarificationPlan:
        questions=[]; blocking=[]
        for conflict in assessment.contradictions:
            question=f"I found conflicting values for {conflict.topic}: {', '.join(conflict.values)}. Which is the current figure?"
            if question not in state.questions_asked: questions.append(question)
        priorities=InformationSufficiencyService().prioritize([*assessment.critical_gaps,*assessment.important_gaps])
        for priority in priorities:
            if priority.gap.can_proceed_without:
                continue
            q=priority.gap.suggested_question
            # On a persisted continuation, questions_asked records previous
            # presentation, not a completed answer.  Keep unanswered critical
            # questions blocking until the authenticated user answers them.
            if (q in state.unresolved_questions or q not in state.questions_asked) and len(questions)<InformationSufficiencyService.max_questions:
                questions.append(q)
                blocking.append(priority.gap)
        return ClarificationPlan(bool(blocking or assessment.contradictions),questions,blocking,assessment.important_gaps,assessment.can_proceed)

class ClarificationStateManager:
    max_rounds=3
    def start(self,state:ClarificationState,plan:ClarificationPlan):
        state.questions_asked.extend(q for q in plan.questions if q not in state.questions_asked); state.unresolved_questions=[q for q in plan.questions if q not in state.questions_answered]; state.clarification_round+=1; state.status="awaiting_answers" if plan.questions else "complete"; return state
    def answer(self,state:ClarificationState,question:str,evidence:EvidenceItem):
        if question in state.unresolved_questions: state.unresolved_questions.remove(question)
        if question not in state.questions_answered: state.questions_answered.append(question)
        state.facts_added.append(evidence); state.status="answered"; return state

def personal_gaps(query: str, decision_type=None) -> list[InformationGap]:
    """Return only Personal-domain gaps; never fall through to Business templates."""
    from app.intelligence_v2.contracts import DecisionType
    text = query.lower()
    gap = InformationGap
    if decision_type is DecisionType.CAREER_DECISION:
        if "two job offers" in text and ("offer a" in text or "offer b" in text): return []
        gaps=[]
        objective_is_explicit = bool(
            any(term in text for term in ("goal", "so that", "choose between", "decide between", "priority"))
            or re.search(r"\b(?:keep|maintain)\s+(?:the\s+)?same\s+income\b", text)
            or re.search(r"\bwork\s+(?:half|fewer|less)\b", text)
        )
        if not objective_is_explicit:
            gaps.append(gap("career_objective", "The intended outcome changes the choice.", GapImportance.CRITICAL, "Advice could optimize for the wrong career outcome.", False, "What career outcome or work result would you most like to gain from a change?"))
        if not any(term in text for term in ("income", "salary", "location", "commute", "time", "hours", "family", "risk", "savings", "remote")):
            gaps.append(gap("career_constraints", "Practical constraints shape viable options.", GapImportance.HIGH, "A suggested path may not fit the user's circumstances.", True, "What practical constraint would most affect this choice, such as income, time, location, or family commitments?"))
        return gaps
    if decision_type is DecisionType.EDUCATION_DECISION:
        gaps=[]
        if not any(term in text for term in ("because", "so that", "goal", "career", "want to")): gaps.append(gap("education_outcome", "The intended outcome determines whether education is a good route.", GapImportance.CRITICAL, "The program may not serve the user's goal.", False, "What do you hope this education will make possible for you?"))
        if not any(term in text for term in ("tuition", "cost", "budget", "afford", "savings", "$")): gaps.append(gap("education_cost", "Cost and financial runway affect feasibility.", GapImportance.HIGH, "The choice may create unexamined financial strain.", True, "What would the program cost, and how would you cover tuition and living expenses?"))
        return gaps
    if decision_type is DecisionType.MAJOR_PURCHASE:
        gaps=[]
        if not re.search(r"\$\s*[\d,]+|\b\d[\d,]*\s*(?:dollars|cad|usd)\b", text): gaps.append(gap("purchase_cost", "Price is needed to assess the trade-off.", GapImportance.CRITICAL, "Affordability cannot be assessed without the cost.", False, "What would the purchase cost, including any near-term fees or financing?"))
        resources_known=bool(re.search(r"\b(?:i\s+have|i(?:'ve| have)\s+saved|savings|income|budget|cash)\s*(?:is|are|of|:)?\s*\$\s*[\d,]+|\bearn(?:ing|s)?\b[^.;]{0,20}?\$\s*[\d,]+|\$\s*[\d,]+\s+(?:in\s+)?(?:savings|income|cash)\b",text))
        if not resources_known: gaps.append(gap("available_resources", "Available resources determine affordability.", GapImportance.CRITICAL, "The purchase could compromise financial safety.", False, "What savings, income, or budget would you use for this purchase?"))
        if not any(term in text for term in ("emergency", "buffer", "keep at least", "reserve")): gaps.append(gap("financial_buffer", "A minimum buffer protects financial resilience.", GapImportance.HIGH, "The purchase may leave too little flexibility.", True, "What minimum savings or emergency buffer do you want to keep after buying it?"))
        return gaps
    if decision_type is DecisionType.PERSONAL_FINANCE:
        gaps=[]
        if not any(term in text for term in ("income", "earn", "salary", "wages")): gaps.append(gap("income", "Income anchors a safe financial comparison.", GapImportance.CRITICAL, "Affordability may be materially misstated.", False, "What income is available, and how stable is it?"))
        if not any(term in text for term in ("expenses", "spend", "debt", "payments", "cost")): gaps.append(gap("obligations", "Recurring obligations determine available cash flow.", GapImportance.CRITICAL, "Advice may ignore required spending.", False, "What regular expenses, debts, or other commitments should be included?"))
        return gaps
    if decision_type is DecisionType.RELOCATION:
        gaps=[]
        if not any(term in text for term in ("for work", "job", "family", "school", "because", "want")): gaps.append(gap("relocation_reason", "The reason for moving determines what matters most.", GapImportance.CRITICAL, "The comparison may optimize for the wrong outcome.", False, "What is prompting the move, and what would a good outcome look like?"))
        if not any(term in text for term in ("rent", "cost", "salary", "budget", "afford", "$")): gaps.append(gap("relocation_finances", "Financial differences affect feasibility.", GapImportance.HIGH, "The move may carry unexamined financial strain.", True, "What income, housing cost, and moving budget would apply in each location?"))
        return gaps
    if decision_type is DecisionType.PERSONAL_PROJECT:
        if any(term in text for term in ("goal", "want to", "so that", "hours", "budget", "launch", "choice", "option")): return []
        return [gap("project_objective", "A clear objective is needed to compare paths.", GapImportance.CRITICAL, "The next step may not serve the intended result.", False, "What are you hoping this project will achieve?"), gap("project_constraints", "Time and budget determine a realistic path.", GapImportance.HIGH, "The plan may exceed available resources.", True, "How much time and money can you realistically give this project?")]
    if decision_type is DecisionType.LIFE_PLANNING:
        # A broad taxonomy label is not itself evidence that the user's focus is
        # missing. Explicit alternatives, deadlines, and priorities can support
        # bounded analysis without inventing facts.
        if re.search(r"\b(?:option\s+[a-z]|which\s+(?:one|option)|choices?|alternatives?|deadline|priority|priorities)\b", text) or re.search(r"\bactually\s+\d+\s+(?:days?|weeks?|months?|years?)\b", text):
            return []
        return [gap("decision_focus", "Aevric AI needs to understand the choice before analyzing it.", GapImportance.CRITICAL, "A recommendation would be premature.", False, "What choice or situation would you like to think through together?")]
    return []

structured_answer_extractor=StructuredAnswerExtractor(); information_sufficiency_service=InformationSufficiencyService(); clarification_planner=ClarificationPlanner(); clarification_state_manager=ClarificationStateManager()
