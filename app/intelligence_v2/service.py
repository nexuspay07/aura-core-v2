"""Internal/test-only entry point for V2 foundation analysis.

It deliberately does not call legacy market, competitive, or random simulation
engines, and is not mounted on the public chat route.
"""

import re

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


class DecisionV2Service:
    def __init__(self, classifier: DecisionClassifier = decision_classifier, assembler: EnterpriseContextAssembler | None = None, gap_detector: InformationGapDetector = information_gap_detector, memory_retriever: MemoryEvidenceRetriever = memory_evidence_retriever, knowledge_adapter: KnowledgeEvidenceAdapter = knowledge_evidence_adapter, document_retriever: DocumentEvidenceRetriever = document_evidence_retriever):
        self.classifier = classifier
        self.assembler = assembler or EnterpriseContextAssembler()
        self.gap_detector = gap_detector
        self.memory_retriever = memory_retriever
        self.knowledge_adapter = knowledge_adapter
        self.document_retriever = document_retriever

    def analyze_request(self, *, db, user_id: int, organization_id: int, workspace_id: int, user_query: str, session_id: int | None = None, decision_scope: str = "business") -> DecisionState:
        context, persisted_evidence = self.assembler.assemble(db=db, user_id=user_id, organization_id=organization_id, workspace_id=workspace_id)
        classification = classify_personal(user_query) if decision_scope == "personal" else self.classifier.classify(user_query)
        request = DecisionRequest(user_id=user_id, organization_id=organization_id, workspace_id=workspace_id, session_id=session_id, user_query=user_query, decision_type=classification.decision_type, objective=classification.decision_type.value, target=self._target(user_query), timeframe=self._timeframe(user_query), constraints=self._constraints(user_query), business_context=context)
        user_evidence = EvidenceItem(id="user-query", source_type=EvidenceSourceType.USER_STATEMENT, source_name="authenticated_user", content=user_query, organization_id=organization_id, workspace_id=workspace_id, permission_scope="session", citation_label="User statement", provenance={"session_id": session_id})
        memory_evidence = self.memory_retriever.retrieve(db=db, organization_id=organization_id, workspace_id=workspace_id, user_id=user_id, query=user_query, session_id=session_id)
        knowledge_evidence = self.knowledge_adapter.retrieve(db=db, organization_id=organization_id, workspace_id=workspace_id, user_id=user_id, query=user_query)
        document_evidence = self.document_retriever.retrieve(db=db, organization_id=organization_id, workspace_id=workspace_id, query=user_query)
        request.memory_context = memory_evidence
        request.knowledge_context = knowledge_evidence
        base_evidence = deduplicate_evidence([user_evidence, *persisted_evidence, *memory_evidence, *knowledge_evidence, *document_evidence])
        # Derived calculations are consequences, not independent source claims;
        # they must not be fed back into conflict detection.
        conflicts = detect_conflicts(base_evidence)
        derived_evidence = derive_decision_evidence(base_evidence, classification.decision_type)
        request.known_facts = deduplicate_evidence([*base_evidence, *derived_evidence_items(derived_evidence, organization_id=organization_id, workspace_id=workspace_id)])
        request.quantitative_context = delivery_cost_reduction_target(request.known_facts, request.target)
        gaps = personal_gaps(user_query, classification.decision_type) if decision_scope == "personal" else self.gap_detector.detect(request, classification)
        request.source_metadata["decision_scope"] = decision_scope
        request.missing_information = gaps
        sufficiency = information_sufficiency_service.assess(request=request, gaps=gaps, conflicts=conflicts)
        clarification_state = ClarificationState()
        clarification = clarification_planner.plan(request=request, assessment=sufficiency, state=clarification_state)
        clarification_state = clarification_state_manager.start(clarification_state, clarification)
        context["quantitative_context"] = request.quantitative_context
        return DecisionState(request=request, classification=classification, assembled_context=context, evidence=request.known_facts, derived_evidence=derived_evidence, information_gaps=gaps, clarification=clarification, confidence=classification.confidence, citations=[item for item in request.known_facts if item.source_type is not EvidenceSourceType.USER_STATEMENT], evidence_conflicts=conflicts, sufficiency=sufficiency, clarification_state=clarification_state, analysis_status="CLARIFICATION_REQUIRED" if clarification.questions else "READY_FOR_ANALYSIS")

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
