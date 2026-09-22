"""Privacy-safe DTOs for the platform Control Center read API."""
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class StrictDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DataCompleteness(StrictDTO):
    user_data: str = "historical"
    saved_decision_data: str = "historical"
    request_telemetry: str
    canonical_telemetry_since: datetime


class WindowedDTO(StrictDTO):
    window_start: datetime
    window_end: datetime
    generated_at: datetime
    data_completeness: DataCompleteness


class UsersMetrics(StrictDTO):
    total_users: int
    new_users_in_window: int
    active_users_in_window: int
    returning_users_in_window: int


class IntelligenceMetrics(StrictDTO):
    total_requests: int
    successful_requests: int
    partial_requests: int
    failed_requests: int
    clarification_requests: int
    safety_requests: int
    operational_reliability_rate: float | None


class DecisionMetrics(StrictDTO):
    total_saved_decisions: int
    new_saved_decisions_in_window: int


class PerformanceMetrics(StrictDTO):
    average_latency_ms: float | None
    p50_latency_ms: int | None
    p95_latency_ms: int | None


class TokenMetrics(StrictDTO):
    known_input_tokens: int
    known_output_tokens: int
    known_reasoning_tokens: int
    known_total_tokens: int
    requests_with_token_data: int
    requests_without_token_data: int


class HealthSummary(StrictDTO):
    status: str = "available"
    telemetry_freshness_at: datetime | None


class OverviewResponse(WindowedDTO):
    users: UsersMetrics
    intelligence: IntelligenceMetrics
    decisions: DecisionMetrics
    performance: PerformanceMetrics
    usage: TokenMetrics
    system: HealthSummary


class UserSummary(StrictDTO):
    user_id: int
    email: str
    full_name: str | None
    created_at: datetime
    is_active: bool
    is_verified: bool
    organization_count: int
    workspace_count: int
    last_intelligence_activity: datetime | None
    request_count_in_window: int
    saved_decision_count: int


class UsersResponse(WindowedDTO):
    items: list[UserSummary]
    next_cursor: str | None
    page_size: int


class DistributionPoint(StrictDTO):
    key: str
    count: int


class TimeSeriesPoint(StrictDTO):
    bucket_start: datetime
    request_count: int
    success_count: int
    failure_count: int


class ProviderCoverage(StrictDTO):
    known_provider_requests: int
    unknown_provider_requests: int
    known_model_requests: int
    unknown_model_requests: int


class ExecutionMetrics(StrictDTO):
    total_retries: int
    requests_with_retries: int
    known_provider_calls: int
    requests_with_provider_call_data: int


class IntelligenceResponse(WindowedDTO):
    total_requests: int
    outcomes: list[DistributionPoint]
    routes: list[DistributionPoint]
    modes: list[DistributionPoint]
    providers: list[DistributionPoint]
    models: list[DistributionPoint]
    error_categories: list[DistributionPoint]
    provider_coverage: ProviderCoverage
    tokens: TokenMetrics
    performance: PerformanceMetrics
    execution: ExecutionMetrics
    bucket: str
    time_series: list[TimeSeriesPoint]
