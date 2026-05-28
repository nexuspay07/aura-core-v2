from app.services.memory_service import (
    save_session_memory,
    get_session_memory,
)

from app.core.cognitive_loop import cognitive_loop
from app.core.user_profile_engine import user_profile_engine


async def process_chat_message(message: str, session_id: str):

    # -------------------------
    # USER PROFILE
    # -------------------------

    profile = user_profile_engine.get_profile(session_id)

    # -------------------------
    # SESSION MEMORY
    # -------------------------

    previous_memories = get_session_memory(session_id)

    # -------------------------
    # SCENARIO
    # -------------------------

    scenario = {
        "goal": message,
        "risk_tolerance": profile.get("risk_tolerance", 0.5),
        "budget": profile.get("budget", 10000),
        "market": "normal"
    }

    # -------------------------
    # COGNITIVE PIPELINE
    # -------------------------

    result = cognitive_loop.run_intelligence_pipeline(
        message,
        scenario,
        profile
    )

    # -------------------------
    # SAVE SESSION MEMORY
    # -------------------------

    save_session_memory(
        session_id,
        "assistant",
        str(result)
    )

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

        "memory_count": len(previous_memories),

        "response": {

            "summary":
                dynamic_reasoning.get(
                    "current_priority"
                ),

            "recommended_strategy":
                best_strategy.get(
                    "name"
                ),

            "strategy_score":
                best_strategy.get(
                    "decision_score"
                ),

            "risk_level":
                best_strategy.get(
                    "risk"
                ),

            "confidence":
                prediction.get(
                    "confidence"
                ),

            "market_insight":
                market.get(
                    "market_pressure"
                ),

            "execution_focus":
                dynamic_reasoning.get(
                    "execution_focus"
                ),

            "next_business_evolution":
                dynamic_reasoning.get(
                    "next_business_evolution"
                ),

            "recommended_operational_move":
                operational.get(
                    "recommended_operational_move"
                ),

            "growth_projection":
                simulation.get(
                    "90_day_projection"
                ),

            "warning":
                dynamic_reasoning.get(
                    "strategic_warning"
                ),

            "next_steps":
                operational.get(
                    "operations_next_steps",
                    []
                )
        }
    }