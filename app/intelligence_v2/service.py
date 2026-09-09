"""Internal/test-only entry point for V2 foundation analysis.

It deliberately does not call legacy market, competitive, or random simulation
engines, and is not mounted on the public chat route.
"""

import re
import time

from app.intelligence_v2.classifier import DecisionClassifier, classify_personal, decision_classifier
from app.intelligence_v2.context import EnterpriseContextAssembler
from app.intelligence_v2.contracts import ClarificationState, DecisionRequest, DecisionState, EvidenceItem, EvidenceSourceType, GapImportance
from app.intelligence_v2.gaps import InformationGapDetector, information_gap_detector
from app.intelligence_v2.retrieval import MemoryEvidenceRetriever, memory_evidence_retriever
from app.intelligence_v2.knowledge import KnowledgeEvidenceAdapter, knowledge_evidence_adapter
from app.intelligence_v2.evidence import deduplicate_evidence, detect_conflicts
from app.intelligence_v2.quantitative import delivery_cost_reduction_target, derived_evidence_items, derive_decision_evidence
from app.intelligence_v2.documents import DocumentEvidenceRetriever, document_evidence_retriever
from app.intelligence_v2.clarification import (clarification_planner, clarification_state_manager, information_sufficiency_service, personal_gaps, structured_answer_extractor)
from app.intelligence_v2.contracts import AssumptionItem, AssumptionStatus, ProceedDecision
from app.intelligence_v2.fact_extraction import extract_fact_ledger, is_business_scenario
from app.intelligence_v2.phase2_adapters import phase2_decision_adapters


_USER_CONTEXT_LIMIT = 12
_CONSTRAINT_PATTERNS = {
    "budget": re.compile(
        r"\b(?:my\s+)?(?:maximum\s+|max\s+)?budget\s+(?:is|was|would be)\s+(?:about\s+)?\$\s*[\d,]+"
        r"|\b(?:i\s+)?(?:actually\s+)?(?:only\s+)?have\s+(?:about\s+)?\$\s*[\d,]+",
        re.I,
    ),
    "deadline": re.compile(
        r"\b(?:(?:(?:my\s+)?deadline\s+(?:is|was)\s+|(?:it\s+is\s+)?actually\s+|(?:i\s+)?only\s+have\s+)"
        r"|(?:within|in)\s+)(?:a|\d+|one|two|three|four|five|six|seven|eight|nine|ten|twelve)\s+"
        r"(?:days?|weeks?|months?|years?)\b",
        re.I,
    ),
    "preference": re.compile(
        r"\b(?:i\s+)?(?:prefer|preferred)\s+option\s+[a-z]\b"
        r"|\b(?:i(?:'ve| have)\s+changed\s+my\s+mind[.;, ]*)?(?:i\s+)?(?:do not|don't|no longer)\s+want\s+option\s+[a-z](?:\s+anymore)?\b",
        re.I,
    ),
    "revenue": re.compile(r"\b(?:monthly\s+)?(?:revenue|mrr)\s+(?:is|was|rose to|fell to|doubled to)?\s*\$\s*[\d,.]+\s*(?:k|m)?",re.I),
    "cash": re.compile(r"\b(?:available\s+)?cash\s+(?:is|was|rose to|fell to)?\s*\$\s*[\d,.]+\s*(?:k|m)?",re.I),
    "runway": re.compile(r"\b(?:runway\s+(?:is|was|rose to|fell to)?\s*)?\d+(?:\.\d+)?\s*(?:days?|weeks?|months?|years?)\s+(?:of\s+)?runway\b",re.I),
    "customer_concentration": re.compile(r"\b(?:largest customer|customer concentration)\b[^.;]{0,30}?\d+(?:\.\d+)?\s*%",re.I),
}


def authoritative_user_context(user_query: str, conversation_turns: list[dict] | None) -> tuple[str, list[dict], dict[str, str]]:
    """Build bounded user-only context; newer explicit constraints supersede older ones."""
    prior = [
        {"content": str(turn.get("content"))[:2000], "original_index": index}
        for index, turn in enumerate((conversation_turns or [])[-_USER_CONTEXT_LIMIT:], start=1)
        if turn.get("role") == "user" and str(turn.get("content") or "").strip()
    ]
    messages = [*prior, {"content": user_query[:2000], "original_index": "current"}]
    matches: list[dict[str, re.Match]] = [
        {slot: match for slot, pattern in _CONSTRAINT_PATTERNS.items() if (match := pattern.search(item["content"]))}
        for item in messages
    ]
    latest = {slot: index for index, item in enumerate(matches) for slot in item}
    authoritative = {slot: matches[index][slot].group(0) for slot, index in latest.items()}
    resolved_prior = []
    for index, item in enumerate(prior):
        content = item["content"]
        superseded = [slot for slot in matches[index] if latest.get(slot, index) > index]
        for slot in superseded:
            content = _CONSTRAINT_PATTERNS[slot].sub("", content, count=1)
        if superseded:
            content = re.sub(r"\s+(?:and|but)\s*[.!?]?\s*$", "", content).strip(" ,;.")
        if content:
            resolved_prior.append({**item, "content": content, "superseded_slots": superseded})
    combined = "\n".join([*(item["content"] for item in resolved_prior), user_query.strip()])
    return combined, resolved_prior, authoritative


class DecisionV2Service:
    def __init__(self, classifier: DecisionClassifier = decision_classifier, assembler: EnterpriseContextAssembler | None = None, gap_detector: InformationGapDetector = information_gap_detector, memory_retriever: MemoryEvidenceRetriever = memory_evidence_retriever, knowledge_adapter: KnowledgeEvidenceAdapter = knowledge_evidence_adapter, document_retriever: DocumentEvidenceRetriever = document_evidence_retriever):
        self.classifier = classifier
        self.assembler = assembler or EnterpriseContextAssembler()
        self.gap_detector = gap_detector
        self.memory_retriever = memory_retriever
        self.knowledge_adapter = knowledge_adapter
        self.document_retriever = document_retriever

    def analyze_request(self, *, db, user_id: int, organization_id: int, workspace_id: int, user_query: str, session_id: int | None = None, decision_scope: str = "business", conversation_turns: list[dict] | None = None) -> DecisionState:
        timings={}
        def measured(name,call):
            started=time.monotonic();result=call();timings[name]=round((time.monotonic()-started)*1000);return result
        context, persisted_evidence = measured("context_assembly_ms",lambda:self.assembler.assemble(db=db, user_id=user_id, organization_id=organization_id, workspace_id=workspace_id))
        decision_context, resolved_turns, authoritative_facts = authoritative_user_context(user_query, conversation_turns)
        fact_ledger = measured("fact_extraction_ms",lambda:extract_fact_ledger(decision_context))
        effective_scope = (
            "business" if is_business_scenario(decision_context, fact_ledger) else "personal"
        ) if decision_scope == "auto" else decision_scope
        classification = classify_personal(decision_context) if effective_scope == "personal" else self.classifier.classify(decision_context)
        objective = fact_ledger["goals"][0] if fact_ledger["goals"] else None
        request = DecisionRequest(user_id=user_id, organization_id=organization_id, workspace_id=workspace_id, session_id=session_id, user_query=decision_context, decision_type=classification.decision_type, objective=objective, target=self._target(decision_context), timeframe=self._timeframe(decision_context), constraints=self._constraints(decision_context), business_context=context)
        user_evidence = EvidenceItem(id="user-query", source_type=EvidenceSourceType.USER_STATEMENT, source_name="authenticated_user", content=user_query, organization_id=organization_id, workspace_id=workspace_id, permission_scope="session", citation_label="User statement", provenance={"session_id": session_id})
        # Only authenticated user statements from this owned session become
        # conversation evidence. Assistant output is never promoted to fact.
        conversation_evidence = [
            EvidenceItem(
                id=f"conversation-turn:{index}", source_type=EvidenceSourceType.USER_STATEMENT,
                source_name="authenticated_conversation", content=str(turn["content"])[:2000],
                organization_id=organization_id, workspace_id=workspace_id,
                permission_scope="session", citation_label="Conversation statement",
                provenance={"session_id": session_id, "turn": turn["original_index"], "superseded_slots": turn["superseded_slots"]},
            )
            for index, turn in enumerate(resolved_turns, start=1)
        ]
        memory_evidence = measured("memory_retrieval_ms",lambda:self.memory_retriever.retrieve(db=db, organization_id=organization_id, workspace_id=workspace_id, user_id=user_id, query=user_query, session_id=session_id))
        knowledge_evidence = measured("knowledge_retrieval_ms",lambda:self.knowledge_adapter.retrieve(db=db, organization_id=organization_id, workspace_id=workspace_id, user_id=user_id, query=user_query))
        document_evidence = measured("document_retrieval_ms",lambda:self.document_retriever.retrieve(db=db, organization_id=organization_id, workspace_id=workspace_id, query=user_query))
        request.memory_context = memory_evidence
        request.knowledge_context = knowledge_evidence
        base_evidence = deduplicate_evidence([user_evidence, *conversation_evidence, *persisted_evidence, *memory_evidence, *knowledge_evidence, *document_evidence])
        # Derived calculations are consequences, not independent source claims;
        # they must not be fed back into conflict detection.
        conflicts = measured("conflict_detection_ms",lambda:detect_conflicts(base_evidence))
        derived_evidence = measured("quantitative_derivation_ms",lambda:derive_decision_evidence(base_evidence, classification.decision_type))
        request.known_facts = deduplicate_evidence([*base_evidence, *derived_evidence_items(derived_evidence, organization_id=organization_id, workspace_id=workspace_id)])
        request.quantitative_context = delivery_cost_reduction_target(request.known_facts, request.target)
        gaps = personal_gaps(decision_context, classification.decision_type) if effective_scope == "personal" else self.gap_detector.detect(request, classification)
        request.source_metadata["decision_scope"] = effective_scope
        request.source_metadata["fact_ledger"] = fact_ledger
        request.source_metadata["timings_ms"] = timings
        request.source_metadata["authoritative_user_constraints"] = authoritative_facts
        request.missing_information = gaps
        sufficiency = information_sufficiency_service.assess(request=request, gaps=gaps, conflicts=conflicts)
        clarification_state = ClarificationState()
        clarification = clarification_planner.plan(request=request, assessment=sufficiency, state=clarification_state)
        clarification_state = clarification_state_manager.start(clarification_state, clarification)
        context["quantitative_context"] = request.quantitative_context
        state=DecisionState(request=request, classification=classification, assembled_context=context, evidence=request.known_facts, derived_evidence=derived_evidence, information_gaps=gaps, clarification=clarification, confidence=classification.confidence, citations=[item for item in request.known_facts if item.source_type is not EvidenceSourceType.USER_STATEMENT], evidence_conflicts=conflicts, sufficiency=sufficiency, clarification_state=clarification_state, analysis_status="CLARIFICATION_REQUIRED" if clarification.should_clarify else "READY_FOR_ANALYSIS")
        return phase2_decision_adapters.enrich(state)

    def apply_clarification_answer(self, *, state: DecisionState, question: str, answer: str) -> DecisionState:
        """Adds session-only user evidence and deterministically re-evaluates state."""
        evidence=structured_answer_extractor.extract(question=question,answer=answer,request=state.request,turn=state.clarification_state.clarification_round)
        clarification_state_manager.answer(state.clarification_state,question,evidence)
        state.request.known_facts.append(evidence); state.evidence.append(evidence)
        # Existing gap detector reads all known facts, including this turn's evidence.
        is_personal = state.request.source_metadata.get("decision_scope") == "personal"
        personal=personal_gaps(state.request.user_query, state.classification.decision_type) if is_personal else []
        # A Personal Ask continuation rebuilds its state from the owned session.
        # Do not keep asking a question which has already received an answer in
        # that session; the answer remains session-scoped evidence.
        answered_fields = {
            gap.field
            for gap in personal
            if gap.suggested_question in state.clarification_state.questions_answered
        }
        personal = [gap for gap in personal if gap.field not in answered_fields]
        gaps=personal if is_personal else self.gap_detector.detect(state.request,state.classification)
        state.request.missing_information=gaps; state.information_gaps=gaps; state.evidence_conflicts=detect_conflicts(state.request.known_facts)
        state.sufficiency=information_sufficiency_service.assess(request=state.request,gaps=gaps,conflicts=state.evidence_conflicts)
        state.clarification=clarification_planner.plan(request=state.request,assessment=state.sufficiency,state=state.clarification_state)
        state.analysis_status="CLARIFICATION_REQUIRED" if state.clarification.should_clarify else "READY_FOR_ANALYSIS"
        return state

    def proceed_with_assumptions(self, state: DecisionState) -> DecisionState:
        assumptions=[AssumptionItem(statement=f"{gap.field} is unknown",source="clarification",confidence=0.0,status=AssumptionStatus.UNVERIFIED,impact_if_wrong=gap.impact_on_decision) for gap in state.information_gaps]
        state.proceed_decision=ProceedDecision(True,assumptions,[gap.impact_on_decision for gap in state.information_gaps if gap.importance in {GapImportance.CRITICAL,GapImportance.HIGH}],[gap.field for gap in state.information_gaps])
        state.assumptions.extend(assumptions); state.analysis_status="READY_FOR_ANALYSIS"; return state

    @staticmethod
    def _target(query: str) -> str | None:
        match = re.search(r"\b(\d+(?:\.\d+)?)\s*%", query)
        return f"{match.group(1)}%" if match else None

    @staticmethod
    def _timeframe(query: str) -> str | None:
        match = re.search(r"\b(?:over|within|in)\s+(?:the\s+next\s+)?(\d+|one|two|three|four|five|six|seven|eight|nine|ten|twelve)\s+(day|days|week|weeks|month|months|year|years)\b", query.lower())
        return f"{match.group(1)} {match.group(2)}" if match else None

    @staticmethod
    def _constraints(query: str) -> list[str]:
        lowered = query.lower()
        constraints = []
        if "without reducing service quality" in lowered or "without reducing quality" in lowered:
            constraints.append("Do not reduce service quality")
        return constraints


decision_v2_service = DecisionV2Service()
