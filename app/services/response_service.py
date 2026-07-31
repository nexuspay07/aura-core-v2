"""
=========================================================

                RESPONSE SERVICE

Converts AuraRequest into the standardized API response.

Responsibilities

• Normalize AuraRequest
• Hide pipeline implementation
• Maintain API contract

=========================================================
"""

from app.core.models.aura_request import AuraRequest
from app.core.models.executive_response import ExecutiveResponse


class ResponseService:

    @staticmethod
    def _items(*values) -> list[str]:
        return [str(value) for value in values if value not in (None, "", [], {})]

    @staticmethod
    def _confidence(value) -> int:
        try:
            value = float(value)
        except (TypeError, ValueError):
            return 50
        if 0 <= value <= 1:
            value *= 100
        return max(0, min(100, round(value)))

    def _build_executive_report(self, request: AuraRequest) -> ExecutiveResponse:
        executive = request.executive
        simulation = request.simulation
        response = request.response
        strategic = executive.strategic_analysis
        market = executive.market_intelligence
        competitive = executive.competitive_intelligence
        business_dna = executive.business_understanding.get("business_dna", {})
        operational = simulation.operational_intelligence
        synthesis = response.synthesis
        confidence = self._confidence(synthesis.get("confidence", executive.executive_analysis.get("confidence", 50)))

        risks = self._items(
            *response.executive_response.get("risks", []),
            executive.dynamic_reasoning.get("strategic_warning"),
            competitive.get("competitive_risk"),
            simulation.strategic_simulation.get("execution_risk"),
        )
        opportunities = self._items(
            market.get("recommended_positioning"),
            executive.executive_analysis.get("primary_opportunity"),
            simulation.strategic_simulation.get("best_case_future"),
        )
        next_actions = self._items(
            *response.executive_response.get("next_steps", []),
            *synthesis.get("next_actions", []),
        )
        roadmap = [
            {"phase": "Validate", "focus": simulation.strategic_simulation.get("30_day_projection", "Validate demand and execution assumptions."), "timeframe": "0–30 days"},
            {"phase": "Systemize", "focus": operational.get("recommended_operational_move", "Document and strengthen the operating model."), "timeframe": "31–60 days"},
            {"phase": "Scale", "focus": simulation.strategic_simulation.get("90_day_projection", "Scale only after the operating model is proven."), "timeframe": "61–90 days"},
        ]

        return ExecutiveResponse(
            executive_summary=response.executive_response.get("executive_summary") or synthesis.get("executive_recommendation", "Aura completed the available executive analysis."),
            situation_overview=executive.executive_analysis.get("summary", "Situation assessment is based on the available business context and deterministic pipeline signals."),
            business_context={"stage": business_dna.get("business_stage", strategic.get("business_stage", "unknown")), "business_model": business_dna.get("business_model", strategic.get("business_model", "unknown")), "objective": strategic.get("primary_objective", "general_strategy"), "priority": executive.dynamic_reasoning.get("current_priority")},
            strategic_analysis={"recommended_focus": executive.executive_analysis.get("recommended_focus"), "verdict": synthesis.get("verdict"), "decision": response.advisor.get("executive_decision"), "reasoning": [item for item in synthesis.get("reasoning", []) if item]},
            market_intelligence={"market_type": market.get("market_type"), "growth_rate": market.get("growth_rate"), "opportunity_score": market.get("opportunity_score"), "threat_score": market.get("threat_score"), "positioning": market.get("recommended_positioning")},
            competitive_intelligence={"intensity": competitive.get("competition_intensity"), "advantage": competitive.get("competitive_advantage"), "moat": competitive.get("recommended_moat"), "risk": competitive.get("competitive_risk")},
            key_risks=list(dict.fromkeys(risks)),
            opportunities=list(dict.fromkeys(opportunities)),
            recommended_strategy={"name": strategic.get("recommended_strategy", "Balanced execution"), "recommendation": synthesis.get("executive_recommendation"), "operational_move": operational.get("recommended_operational_move")},
            implementation_roadmap=roadmap,
            plan_30_60_90=roadmap,
            kpis=[
                {"name": "Market opportunity", "value": market.get("opportunity_score", "Unknown"), "unit": "score"},
                {"name": "Market threat", "value": market.get("threat_score", "Unknown"), "unit": "score"},
                {"name": "Scale readiness", "value": operational.get("scale_readiness", "Unknown"), "unit": "assessment"},
                {"name": "Execution load", "value": operational.get("execution_load", "Unknown"), "unit": "assessment"},
            ],
            confidence={"score": confidence, "level": "high" if confidence >= 75 else "moderate" if confidence >= 50 else "low", "basis": "Deterministic executive, market, competitive, and simulation signals."},
            assumptions=["Analysis uses the supplied goal, stored business context, and deterministic platform engines.", "No external market research or live-source validation was used."],
            sources=["Strategic Analysis Engine", "Market Intelligence Engine", "Competitive Intelligence Engine", "Simulation Pipeline", "Operational Intelligence Engine"],
            suggested_next_actions=list(dict.fromkeys(next_actions)) or ["Validate the primary recommendation with an accountable owner and measurable outcome."],
            raw_response=response.model_dump(),
        )

    def build_response(

        self,

        *,

        request: AuraRequest,

        session_id: str | None = None,

    ) -> dict:

        executive = request.executive

        simulation = request.simulation

        response = request.response

        business = request.business_context or {}

        standardized = response.standardized

        executive_report = self._build_executive_report(request)

        return {

            "success": True,

            "session_id": session_id,

            "organization": business.get(
                "organization_name"
            ),

            "workspace": business.get(
                "workspace_name"
            ),

            "profile": request.profile,

            "memory": request.memory,

            "goal": request.goal,

            "executive": executive.model_dump(),

            "simulation": simulation.model_dump(),

            "response": response.model_dump(),

            "standardized_output": standardized,

            "executive_report": executive_report.model_dump(),

        }


response_service = ResponseService()
