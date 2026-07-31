"""Persistence- and payment-provider-agnostic Commercial Platform contracts."""
from abc import ABC, abstractmethod
from enum import StrEnum
from decimal import Decimal

from pydantic import BaseModel, Field

class SubscriptionStatus(StrEnum): TRIAL = "trial"; ACTIVE = "active"; PAUSED = "paused"; CANCELLED = "cancelled"; EXPIRED = "expired"; GRACE = "grace"
class PlanDefinition(BaseModel):
    key: str; name: str; limits: dict[str, int | None] = Field(default_factory=dict); features: set[str] = Field(default_factory=set); metadata: dict = Field(default_factory=dict)
class Subscription(BaseModel):
    subject_type: str; subject_id: str; plan_key: str; status: SubscriptionStatus; billing_period: str = "monthly"; provider_reference: str | None = None
class EntitlementDecision(BaseModel):
    """Read-only commercial entitlement resolution result."""
    organization_id: int
    feature_key: str
    is_entitled: bool
    value_type: str | None = None
    boolean_value: bool | None = None
    integer_value: int | None = None
    decimal_value: Decimal | None = None
    string_value: str | None = None
    source_plan_id: int | None = None
    source_subscription_id: int | None = None
    reason: str
class UsageRecord(BaseModel):
    subject_type: str; subject_id: str; metric: str; quantity: int = 1; metadata: dict = Field(default_factory=dict)
class PaymentProvider(ABC):
    key: str
    @abstractmethod
    def create_checkout(self, subscription: Subscription) -> str: ...
class SubscriptionRepository(ABC):
    @abstractmethod
    def get_active(self, subject_type: str, subject_id: str) -> Subscription | None: ...
