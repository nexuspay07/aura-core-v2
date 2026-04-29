from fastapi import APIRouter
from app.core.pro_report_engine import pro_report_engine

router = APIRouter()


@router.post("/pro-report")
def generate_pro_report(data: dict):
    goal = data.get("goal")
    decision = data.get("decision_brief", {})
    comparison = data.get("strategy_comparison", {})

    report = pro_report_engine.generate(goal, decision, comparison)

    return {
        "type": "pro_report",
        "report": report
    }