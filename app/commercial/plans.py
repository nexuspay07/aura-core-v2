"""Config-driven plan catalog; plans are supplied at bootstrap/deployment, not hardcoded in services."""
from app.commercial.contracts import PlanDefinition

class PlanCatalog:
    def __init__(self, plans: list[PlanDefinition] = ()) -> None: self._plans = {plan.key: plan for plan in plans}
    def get(self, key: str) -> PlanDefinition: return self._plans[key]
    def register(self, plan: PlanDefinition) -> None:
        if plan.key in self._plans: raise ValueError(f"Plan '{plan.key}' already exists.")
        self._plans[plan.key] = plan
    def manifest(self) -> list[dict]: return [plan.model_dump(mode="json") for _, plan in sorted(self._plans.items())]
