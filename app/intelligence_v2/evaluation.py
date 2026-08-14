"""Offline-only V2 quality cases; never persisted or sent to providers by default."""
EVALUATION_CASES = (
    "cost_reduction", "career_choice", "pricing", "hiring", "investment",
    "insufficient_information", "contradictory_evidence", "memory_recall", "document_grounded",
)

EVALUATION_DIMENSIONS = ("context_use", "constraint_adherence", "evidence_grounding", "specificity", "actionability", "risk_awareness", "assumption_discipline", "citation_accuracy", "non_fabrication")
