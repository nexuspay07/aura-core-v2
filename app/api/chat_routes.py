from fastapi import APIRouter
from pydantic import BaseModel

from sqlalchemy import insert

from app.db.database import SessionLocal

from app.db.intelligence_session_table import (
    intelligence_session_table
)

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
    
    print("\n========== AURA RESULT ==========")
    print(result)
    print("=================================\n")

    strategic_analysis = (
    result.get(
        "strategic_analysis"
    )
    or {}
)

    print(
    "\nSTRATEGIC ANALYSIS:\n",
    strategic_analysis
)

    print(
    result.get(
        "strategic_analysis"
    )
)

    print("\n========== TOP LEVEL KEYS ==========")
    print(result.keys())
    print("====================================\n")

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

    response_data = {
        "success": True,

        "response": {

            # ==========================================
            # PHASE 64.6 EXECUTIVE INTELLIGENCE
            # ==========================================

            "executive_summary":

                strategic_analysis.get(
                    "recommended_focus"
                )

                or

                dynamic_reasoning.get(
                    "executive_summary"
                )

                or

                f"Strategic analysis completed for: {message}",

            "strategic_position":

                f"""
Business Stage:
{strategic_analysis.get('business_stage', 'unknown')}

Primary Objective:
{strategic_analysis.get('objective', 'unknown')}
""",

            "market_analysis":

                f"""
Opportunity:
{strategic_analysis.get('opportunity', 'unknown')}

Threat:
{strategic_analysis.get('threat', 'unknown')}
""",

            "growth_strategy":

                best_strategy.get(
                    "name"
                )

                or

                "Balanced Strategic Growth",

            "operational_plan":

                strategic_analysis.get(
                    "recommended_focus"
                )

                or

                "Operational plan unavailable.",

            "strategic_warning":

                dynamic_reasoning.get(
                    "strategic_warning"
                )

                or

                "No major strategic warnings identified.",

            # ==========================================
            # LEGACY RESPONSE FIELDS
            # ==========================================

            "summary":

                strategic_analysis.get(
                    "recommended_focus"
                )

                or

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

                strategic_analysis.get(
                    "recommended_focus"
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

                strategic_analysis.get(
                    "recommended_focus"
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

        # ==========================================
    # SAVE INTELLIGENCE SESSION
    # ==========================================

    try:

        db = SessionLocal()

        query = insert(
            intelligence_session_table
        ).values(

            organization_id=(
                data.organization_id or 1
            ),

            workspace_id=(
                data.workspace_id or 1
            ),

            created_by_user_id=1,

            title=message[:100],

            goal=message,

            domain="business",

            session_type="decision_analysis",

            status="completed",

            summary=response_data[
                "response"
            ]["summary"],

            recommended_move=response_data[
                "response"
            ]["recommended_strategy"],

            risk_level=response_data[
                "response"
            ]["risk_level"],

            report_json=response_data["response"],

            business_model="business",

            is_active=True
        )

        db.execute(query)

        db.commit()

        print(
            "[AURA] Intelligence session saved"
        )

    except Exception as e:

        print(
            f"[AURA] Session save failed: {e}"
        )

    finally:

        db.close()

    return response_data