
from fastapi import APIRouter
from pydantic import BaseModel

from app.services.chat_service import process_chat_message


from app.core.memory.conversation_engine import conversation_engine
from app.core.user_profile_engine import user_profile_engine
from app.core.conversation_memory import conversation_memory
from app.core.decision_memory_engine import decision_memory_engine

from app.core.simulation.prediction_engine import prediction_engine
from app.core.uncertainty_engine import uncertainty_engine
from app.core.decision_memory_engine import decision_memory_engine
from app.core.adaptive_learning_v2_engine import adaptive_learning_v2_engine
from app.core.strategy_reinforcement_engine import strategy_reinforcement_engine
from app.core.reasoning.causal_reasoning_engine import causal_reasoning_engine
from app.core.strategic_evolution_engine import strategic_evolution_engine

from app.domains.business.business_domain_engine import business_domain_engine
from app.domains.healthcare.healthcare_engine import healthcare_engine
from app.core.cognitive_loop import (
    cognitive_loop
)

router = APIRouter()


class ConversationRequest(BaseModel):
    message: str
    session_id: str | None = None
    organization_id: int | None = None
    workspace_id: int | None = None


def is_healthcare_message(message: str) -> bool:
    keywords = [
        "pain", "fever", "cough", "headache", "fatigue",
        "dizziness", "shortness of breath", "chest pain",
        "symptom", "medical", "health"
    ]

    return any(k in message.lower() for k in keywords)


@router.post("/chat")
async def chat(data: ConversationRequest):

    session_id = data.session_id or "default-session"

    

    # -------------------------
    # USER PROFILE
    # -------------------------

    profile = user_profile_engine.get_profile(
    session_id
)

    scenario = {
    "goal": data.message,
    "risk_tolerance": profile.get(
        "risk_tolerance",
        0.5
    ),
    "budget": profile.get(
        "budget",
        10000
    ),
    "market": "normal"
}

    # -------------------------
    # SIMPLE SCENARIO
    # -------------------------

    scenario = {
        "goal": data.message,
        "risk_tolerance": profile.get("risk_tolerance", 0.5),
        "budget": profile.get("budget", 10000),
        "market": "normal"
    }

    # -------------------------
    # COGNITIVE PIPELINE
    # -------------------------

    try:

        result = cognitive_loop.run_intelligence_pipeline(
            data.message,
            scenario,
            profile
        )

    except Exception as e:

        return {
            "status": "error",
            "error": str(e)
        }

    # -------------------------
    # RESPONSE NORMALIZATION
    # -------------------------

    best_strategy = result.get(
        "best_strategy",
        {}
    )

    dynamic_reasoning = result.get(
        "dynamic_reasoning",
        {}
    )

    prediction = result.get(
        "prediction",
        {}
    )

    operational = result.get(
        "operational_intelligence",
        {}
    )

    market = result.get(
        "market_intelligence",
        {}
    )

    simulation = result.get(
        "strategic_simulation",
        {}
    )

    return {

        "status": "success",

        "session_id": session_id,

        "profile": profile,

        "response": {

    "summary":
        dynamic_reasoning.get(
            "current_priority"
        )
        or business_understanding.get(
            "strategic_direction"
        )
        or "AURA generated strategic analysis.",

    "recommended_strategy":
        best_strategy.get(
            "name"
        )
        or "Balanced Strategic Growth",

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
        or business_understanding.get(
            "market_nature"
        )
        or "Market conditions require strategic positioning.",

    "execution_focus":
        dynamic_reasoning.get(
            "execution_focus"
        )
        or "Focus on disciplined execution and operational efficiency.",

    "next_business_evolution":
        dynamic_reasoning.get(
            "next_business_evolution"
        )
        or "Improve systems and validate customer demand.",

    "recommended_operational_move":
        operational.get(
            "recommended_operational_move"
        )
        or "Strengthen operational consistency and execution systems.",

    "growth_projection":
        simulation.get(
            "90_day_projection"
        )
        or "Moderate growth potential with disciplined execution.",

    "warning":
        dynamic_reasoning.get(
            "strategic_warning"
        )
        or "Avoid scaling too aggressively without validated demand.",

    "reinforcement_status":
        reinforcement.get(
            "reinforcement_status"
        )
        or "Learning patterns still evolving.",

    "reinforcement_recommendation":
        reinforcement.get(
            "reinforcement_recommendation"
        )
        or "Continue gathering strategic execution data.",

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