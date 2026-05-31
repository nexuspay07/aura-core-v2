from fastapi import APIRouter
from pydantic import BaseModel

from app.core.user_profile_engine import (
    user_profile_engine
)

from app.core.cognitive_loop import (
    cognitive_loop
)

router = APIRouter()


# ==========================================
# REQUEST MODEL
# ==========================================

class ConversationRequest(BaseModel):
    message: str
    session_id: str | None = None
    organization_id: int | None = None
    workspace_id: int | None = None


# ==========================================
# CHAT ROUTE
# ==========================================

@router.post("/chat")
async def chat(data: ConversationRequest):

    session_id = (
        data.session_id
        or "default-session"
    )

    tenant_id = (
        str(data.organization_id)
        if data.organization_id
        else "default-tenant"
    )

    message = data.message

    # ==========================================
    # USER PROFILE
    # ==========================================

    profile = (
        user_profile_engine.get_profile(
            session_id
        )
    )

    # ==========================================
    # EXECUTIVE SCENARIO
    # ==========================================

    scenario = {
        "goal": message,

        "risk_tolerance":
            profile.get(
                "risk_tolerance",
                0.5
            ),

        "budget":
            profile.get(
                "budget",
                10000
            ),

        "market": "normal"
    }

    # ==========================================
    # RUN COGNITIVE PIPELINE
    # ==========================================

    result = (
    cognitive_loop
    .run_intelligence_pipeline(
        goal=message,
        scenario=scenario,
        profile=profile
    )
)

    # ==========================================
    # SAFE EXTRACTIONS
    # ==========================================

    business_understanding = (
        result.get(
            "business_understanding"
        )
        or {}
    )

    dynamic_reasoning = (
        result.get(
            "dynamic_reasoning"
        )
        or {}
    )

    best_strategy = (
        result.get(
            "best_strategy"
        )
        or {}
    )

    prediction = (
        result.get(
            "prediction"
        )
        or {}
    )

    market = (
    result.get("market_intelligence")
    or {}
)

    operational = (
    result.get("operational_intelligence")
    or {}
)

    simulation = (
    result.get("strategic_simulation")
    or {}
)

    reinforcement = (
    result.get("strategy_reinforcement")
    or {}
)

    memory_summary = (
        result.get(
            "memory_summary"
        )
        or {}
    )

    # ==========================================
    # FINAL RESPONSE
    # ==========================================

    return {

        "success": True,

        "response": {

            "summary":

    dynamic_reasoning.get(
        "current_priority"
    )

    or

    dynamic_reasoning.get(
        "executive_summary"
    )

    or

    business_understanding.get(
        "strategic_direction"
    )

    or

    f"Strategic analysis completed for: {message}",

            "recommended_strategy":

                best_strategy.get(
                    "name"
                )

                or

                "Balanced Strategic Growth",

            "strategy_score":

                best_strategy.get(
                    "decision_score"
                )

                or 75,

            "risk_level":

                best_strategy.get(
                    "risk"
                )

                or "medium",

            "confidence":

                prediction.get(
                    "confidence"
                )

                or 0.72,

            "market_insight":

                market.get(
                    "market_pressure"
                )

                or

                business_understanding.get(
                    "market_nature"
                )

                or

                "Market conditions require strategic positioning.",

            "execution_focus":

                dynamic_reasoning.get(
                    "execution_focus"
                )

                or

                "Focus on disciplined execution and operational efficiency.",

            "next_business_evolution":

                dynamic_reasoning.get(
                    "next_business_evolution"
                )

                or

                "Improve systems and validate customer demand.",

            "recommended_operational_move":

                operational.get(
                    "recommended_operational_move"
                )

                or

                "Strengthen operational consistency and execution systems.",

            "growth_projection":

                simulation.get(
                    "90_day_projection"
                )

                or

                "Moderate growth potential with disciplined execution.",

            "warning":

                dynamic_reasoning.get(
                    "strategic_warning"
                )

                or

                "Avoid scaling too aggressively without validated demand.",

            "reinforcement_status":

                reinforcement.get(
                    "reinforcement_status"
                )

                or

                "Learning patterns still evolving.",

            "reinforcement_recommendation":

                reinforcement.get(
                    "reinforcement_recommendation"
                )

                or

                "Continue gathering strategic execution data.",

            "memory_summary":

                memory_summary

                or {
                    "summary":
                    "Strategic memory systems active."
                },

            "next_steps":

                operational.get(
                    "operations_next_steps",
                    []
                )

                or [

                    "Validate market demand",

                    "Improve operational systems",

                    "Strengthen strategic positioning"
                ]
        }
    }