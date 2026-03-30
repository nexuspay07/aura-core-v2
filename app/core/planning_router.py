from fastapi import APIRouter
from app.core.planning_engine import planning_engine

router = APIRouter(prefix="/planning", tags=["Autonomous Planning"])


@router.post("/create/{goal_id}")
def create_plan(goal_id: str):

    plan = planning_engine.create_plan_for_goal(goal_id)

    if not plan:
        return {
            "status": "goal_not_found"
        }

    return {
        "status": "plan_created",
        "plan": plan
    }


@router.post("/execute/{plan_id}")
def execute_step(plan_id: str):

    plan = planning_engine.execute_next_step(plan_id)

    if not plan:
        return {
            "status": "plan_not_found"
        }

    return {
        "status": "step_executed",
        "plan": plan
    }


@router.get("/status")
def planning_status():

    return planning_engine.get_status()


@router.get("/active")
def active_plans():

    return planning_engine.get_active_plans()


@router.get("/history")
def planning_history():

    return planning_engine.get_plan_history()