"""Authenticated, ephemeral product exposure for direct Strategy generation."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field

from app.api.auth_routes import get_current_user_from_token
from app.intelligence_v2.model_provider import (
    InvalidModelResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from app.strategy.capability import strategy_capability
from app.strategy.contracts import (
    ConfidenceLevel,
    StrategyAssumption,
    StrategyConstraint,
    StrategyInput,
    StrategyResource,
    StrategyRisk,
    StrategyScope,
)
from app.strategy.orchestrator import StrategyGenerationError
from app.strategy.presentation import StrategyPresentation, to_strategy_presentation
from app.strategy.quality import StrategyQualityError
from app.strategy.validation import StrategyValidationError


router = APIRouter(prefix="/strategies", tags=["Strategy"])
security = HTTPBearer()


class StrategyResourceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=160)
    description: str = Field(min_length=1, max_length=1000)


class StrategyRiskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    risk: str = Field(min_length=1, max_length=1000)
    mitigation: str | None = Field(default=None, min_length=1, max_length=1000)


class DirectStrategyRequest(BaseModel):
    """Product input only; authentication and tenant identity are excluded."""

    model_config = ConfigDict(extra="forbid")

    objective: str = Field(min_length=1, max_length=4000)
    chosen_direction: str = Field(min_length=1, max_length=4000)
    constraints: list[str] = Field(default_factory=list, max_length=50)
    resources: list[StrategyResourceRequest] = Field(default_factory=list, max_length=50)
    assumptions: list[str] = Field(default_factory=list, max_length=50)
    risks: list[StrategyRiskRequest] = Field(default_factory=list, max_length=50)
    uncertainties: list[str] = Field(default_factory=list, max_length=50)
    time_horizon: str | None = Field(default=None, min_length=1, max_length=500)
    change_conditions: list[str] = Field(default_factory=list, max_length=50)


async def current_identity(credentials: HTTPAuthorizationCredentials = Depends(security)):
    return await get_current_user_from_token(credentials)


def authorized_scope(identity: dict) -> StrategyScope:
    """Build scope only from the server-resolved persisted identity."""

    user = identity.get("user") or {}
    if not isinstance(user.get("id"), int):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    organization = identity.get("organization") or {}
    workspace = identity.get("workspace") or {}
    organization_id = organization.get("id")
    workspace_id = workspace.get("id")
    if not (isinstance(organization_id, int) and isinstance(workspace_id, int)):
        organization_id = None
        workspace_id = None

    return StrategyScope(
        user_id=user["id"],
        organization_id=organization_id,
        workspace_id=workspace_id,
    )


def to_strategy_input(body: DirectStrategyRequest, scope: StrategyScope) -> StrategyInput:
    """Map explicit product input into the canonical direct-Strategy contract."""

    return StrategyInput(
        scope=scope,
        objective=body.objective,
        chosen_direction=body.chosen_direction,
        constraints=tuple(
            StrategyConstraint(f"direct-constraint-{index:03d}", statement)
            for index, statement in enumerate(body.constraints, start=1)
        ),
        resources=tuple(
            StrategyResource(item.name, item.description) for item in body.resources
        ),
        assumptions=tuple(
            StrategyAssumption(statement, "user_provided") for statement in body.assumptions
        ),
        risks=tuple(StrategyRisk(item.risk, item.mitigation) for item in body.risks),
        uncertainties=tuple(body.uncertainties),
        time_horizon=body.time_horizon,
        change_conditions=tuple(body.change_conditions),
        confidence=ConfidenceLevel.LOW,
    )


@router.post(
    "",
    response_model=StrategyPresentation,
    summary="Develop a strategy for a chosen direction",
)
async def generate_strategy(
    body: DirectStrategyRequest,
    identity=Depends(current_identity),
) -> StrategyPresentation:
    """Generate and return an ephemeral Strategy without persisting it."""

    strategy_input = to_strategy_input(body, authorized_scope(identity))
    try:
        result = strategy_capability.generate(strategy_input)
        return to_strategy_presentation(result)
    except ProviderTimeoutError as error:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Strategy generation timed out. Please try again.",
        ) from error
    except ProviderUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Strategy generation is temporarily unavailable.",
        ) from error
    except InvalidModelResponseError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Strategy generation could not produce a valid response.",
        ) from error
    except (StrategyValidationError, StrategyQualityError, StrategyGenerationError) as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Strategy input or generated output did not pass validation.",
        ) from error
