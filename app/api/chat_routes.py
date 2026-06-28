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
    # MODERN AURA RESPONSE
    # ==========================================

    executive_response = (
        result.get("executive_response")
        or {}
    )

    executive_synthesis = (
        result.get("executive_synthesis")
        or {}
    )

    final_response = (
        result.get("final_response")
        or {}
    )

    standardized_output = (
        result.get("standardized_output")
        or {}
    )

    executive_advisor = (
        result.get("executive_advisor")
        or {}
    )

    conversational_response = (
        result.get("conversational_response")
        or {}
    )

    chat_response = (
        result.get("chat_response")
        or {}
    )

    conversation_history = (
        result.get("conversation_history")
        or []
    )

    response_data = {

        "success": True,

        "chat_response": chat_response,

        "executive_advisor": executive_advisor,

        "conversational_response":
            conversational_response,

        "standardized_output":
            standardized_output,

        "executive_response":
            executive_response,

        "executive_synthesis":
            executive_synthesis,

        "final_response":
            final_response,

        "conversation_history":
            conversation_history,

        "pipeline": result
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

            summary=chat_response.get(
    "message",
    ""
),

            recommended_move=executive_advisor.get(
    "advisor_recommendation",
    ""
),

            risk_level=chat_response.get(
    "warning",
    "medium"
),
            report_json=response_data,

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