"""Canonical, provider-neutral contracts for decision intelligence."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class DecisionType(str, Enum):
    CAREER_DECISION = "career_decision"
    EDUCATION_DECISION = "education_decision"
    MAJOR_PURCHASE = "major_purchase"
    PERSONAL_FINANCE = "personal_finance"
    PERSONAL_PROJECT = "personal_project"
    RELOCATION = "relocation"
    LIFE_PLANNING = "life_planning"
    OPERATIONAL_OPTIMIZATION = "operational_optimization"
    COST_REDUCTION = "cost_reduction"
    PRICING = "pricing"
    HIRING = "hiring"
    MARKET_EXPANSION = "market_expansion"
    INVESTMENT = "investment"
    PRODUCT_LAUNCH = "product_launch"
    SALES_GROWTH = "sales_growth"
    CUSTOMER_RETENTION = "customer_retention"
    SUPPLY_CHAIN = "supply_chain"
    FINANCIAL_PLANNING = "financial_planning"
    RISK_MANAGEMENT = "risk_management"
    STRATEGIC_PLANNING = "strategic_planning"
    GENERAL_BUSINESS_ANALYSIS = "general_business_analysis"


class EvidenceSourceType(str, Enum):
    ORGANIZATION_PROFILE = "organization_profile"
    WORKSPACE_CONTEXT = "workspace_context"
    MEMORY = "memory"
    KNOWLEDGE_DOCUMENT = "knowledge_document"
    OPERATIONAL_DATA = "operational_data"
    COMMERCIAL_DATA = "commercial_data"
    SIMULATION = "simulation"
    EXTERNAL_SOURCE = "external_source"
    USER_STATEMENT = "user_statement"


class AssumptionStatus(str, Enum):
    CONFIRMED = "confirmed"
    INFERRED = "inferred"
    UNVERIFIED = "unverified"
    CONTRADICTED = "contradicted"

class ClaimType(str, Enum):
    FACT = "fact"
    DERIVED_FACT = "derived_fact"
    ASSUMPTION = "assumption"
    UNRESOLVED_FACTOR = "unresolved_factor"
    RECOMMENDATION = "recommendation"
    GENERAL_REASONING = "general_reasoning"


class GapImportance(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class SufficiencyStatus(str, Enum):
    INSUFFICIENT = "insufficient"
    PARTIALLY_SUFFICIENT = "partially_sufficient"
    SUFFICIENT = "sufficient"
    CONTRADICTORY = "contradictory"


@dataclass(frozen=True)
class DecisionClassification:
    decision_type: DecisionType
    secondary_types: list[DecisionType]
    confidence: float
    rationale: list[str]
    required_data_domains: list[str]


@dataclass(frozen=True)
class EvidenceItem:
    id: str
    source_type: EvidenceSourceType
    source_name: str
    content: str | None = None
    structured_value: Any = None
    unit: str | None = None
    organization_id: int | None = None
    workspace_id: int | None = None
    timestamp: datetime | None = None
    freshness: str | None = None
    reliability: str | None = None
    permission_scope: str | None = None
    citation_label: str | None = None
    provenance: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EvidenceConflict:
    """Comparable claims that V2 must surface rather than resolve silently."""

    topic: str
    evidence_ids: list[str]
    values: list[str]
    message: str


@dataclass(frozen=True)
class CitationReference:
    """A citation always maps to one authorized persisted evidence source."""

    citation_id: str
    evidence_id: str
    document_id: int
    chunk_id: int
    source_name: str
    page: int | None
    section: str | None
    source_type: EvidenceSourceType


@dataclass(frozen=True)
class AssumptionItem:
    statement: str
    source: str
    confidence: float
    status: AssumptionStatus
    impact_if_wrong: str


@dataclass(frozen=True)
class InformationGap:
    field: str
    why_needed: str
    importance: GapImportance
    impact_on_decision: str
    can_proceed_without: bool
    suggested_question: str

@dataclass(frozen=True)
class GapPriority:
    gap: InformationGap
    score: int
    rationale: list[str]

@dataclass(frozen=True)
class InformationSufficiencyAssessment:
    status: SufficiencyStatus
    evidence_coverage: dict[str, bool]
    critical_gaps: list[InformationGap]
    important_gaps: list[InformationGap]
    optional_gaps: list[InformationGap]
    contradictions: list[EvidenceConflict]
    assumptions_required: list[str]
    can_proceed: bool
    recommended_action: str
    rationale: list[str]

@dataclass
class ClarificationState:
    questions_asked: list[str] = field(default_factory=list)
    questions_answered: list[str] = field(default_factory=list)
    unresolved_questions: list[str] = field(default_factory=list)
    facts_added: list[EvidenceItem] = field(default_factory=list)
    contradictions_resolved: list[str] = field(default_factory=list)
    clarification_round: int = 0
    status: str = "not_started"

@dataclass(frozen=True)
class ProceedDecision:
    allowed: bool
    assumptions_required: list[AssumptionItem]
    material_risks: list[str]
    limitations: list[str]

@dataclass(frozen=True)
class AnalysisPackage:
    decision: dict[str, Any]
    context: dict[str, Any]
    evidence: list[dict[str, Any]]
    assumptions: list[dict[str, Any]]
    contradictions: list[dict[str, Any]]
    tools: dict[str, Any]
    limitations: list[str]

@dataclass(frozen=True)
class AnalysisAlternative:
    option: str
    benefits: list[str]
    downsides: list[str]
    evidence_ids: list[str]
    assumptions: list[str]
    conditions_for_success: list[str]

@dataclass(frozen=True)
class AnalysisRecommendation:
    recommended_option: str
    rationale: str
    expected_effect: str
    prerequisites: list[str]
    what_would_change_the_recommendation: list[str]

@dataclass(frozen=True)
class ModelAnalysisAlternative:
    """The compact, provider-facing alternative contract."""

    option: str
    benefits: list[str]
    downsides: list[str]
    evidence_ids: list[str]
    assumptions: list[str]
    conditions_for_success: list[str]

@dataclass(frozen=True)
class ModelAnalysisResult:
    """Semantic reasoning returned by a model before Aura augments it."""

    problem_summary: str
    alternatives: list[ModelAnalysisAlternative]
    recommended_option: str
    rationale: str
    key_tradeoffs: list[str]
    risks: list[str]
    assumptions_used: list[str]
    evidence_ids: list[str]
    unresolved_questions: list[str]
    recommendation_change_conditions: list[str]

@dataclass(frozen=True)
class DerivedEvidence:
    """A reproducible fact calculated solely from authorized evidence."""

    id: str
    claim: str
    calculation: str
    source_evidence_ids: list[str]
    numeric_values: list[str]
    operation: str = ""
    source_values: dict[str, str] = field(default_factory=dict)
    unit: str | None = None
    semantic_label: str = ""
    decision_relevance: str = ""

@dataclass(frozen=True)
class AnalysisResult:
    problem_understanding: str
    key_facts: list[str]
    assumptions_used: list[str]
    alternatives: list[AnalysisAlternative]
    analysis: str
    risks: list[str]
    recommendation: AnalysisRecommendation
    prioritized_actions: list[str]
    unresolved_questions: list[str]
    evidence_used: list[str]
    citations: list[str]
    limitations: list[str]
    derived_facts: list[str]

@dataclass(frozen=True)
class AnalysisExecution:
    status: str
    result: AnalysisResult | None
    confidence: str | None
    confidence_rationale: list[str]
    critique_findings: list[str]
    usage: dict[str, Any]


@dataclass(frozen=True)
class ClarificationPlan:
    should_clarify: bool
    questions: list[str]
    blocking_gaps: list[InformationGap]
    nonblocking_gaps: list[InformationGap]
    proceed_with_assumptions: bool


@dataclass
class DecisionRequest:
    user_id: int
    organization_id: int
    workspace_id: int
    user_query: str
    session_id: int | None = None
    decision_type: DecisionType | None = None
    objective: str | None = None
    target: str | None = None
    timeframe: str | None = None
    constraints: list[str] = field(default_factory=list)
    known_facts: list[EvidenceItem] = field(default_factory=list)
    assumptions: list[AssumptionItem] = field(default_factory=list)
    missing_information: list[InformationGap] = field(default_factory=list)
    business_context: dict[str, Any] = field(default_factory=dict)
    memory_context: list[EvidenceItem] = field(default_factory=list)
    knowledge_context: list[EvidenceItem] = field(default_factory=list)
    external_evidence: list[EvidenceItem] = field(default_factory=list)
    quantitative_context: dict[str, Any] = field(default_factory=dict)
    source_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DecisionState:
    request: DecisionRequest
    classification: DecisionClassification
    assembled_context: dict[str, Any]
    evidence: list[EvidenceItem] = field(default_factory=list)
    derived_evidence: list[DerivedEvidence] = field(default_factory=list)
    assumptions: list[AssumptionItem] = field(default_factory=list)
    information_gaps: list[InformationGap] = field(default_factory=list)
    clarification: ClarificationPlan | None = None
    selected_tools: list[str] = field(default_factory=list)
    analysis_outputs: dict[str, Any] = field(default_factory=dict)
    risks: list[str] = field(default_factory=list)
    alternatives: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    confidence: float = 0.0
    verification: dict[str, Any] = field(default_factory=dict)
    citations: list[EvidenceItem] = field(default_factory=list)
    evidence_conflicts: list[EvidenceConflict] = field(default_factory=list)
    sufficiency: InformationSufficiencyAssessment | None = None
    clarification_state: ClarificationState = field(default_factory=ClarificationState)
    proceed_decision: ProceedDecision | None = None
    analysis_status: str = "CLARIFICATION_REQUIRED"
