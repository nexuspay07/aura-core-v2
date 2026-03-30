from fastapi import APIRouter
from app.core.goal_engine import goal_engine

router = APIRouter(prefix="/goals", tags=["Autonomous Goals"])


@router.post("/generate")
def generate_goal():

    goal = goal_engine.generate_goal()

    return {
        "status": "goal_created",
        "goal": goal
    }


@router.post("/complete/{goal_id}")
def complete_goal(goal_id: str):

    goal = goal_engine.complete_goal(goal_id)

    if goal:
        return {
            "status": "goal_completed",
            "goal": goal
        }

    return {
        "status": "goal_not_found"
    }


@router.get("/status")
def goal_status():

    return goal_engine.get_status()


@router.get("/active")
def active_goals():

    return goal_engine.get_active_goals()


@router.get("/history")
def goal_history():

    return goal_engine.get_goal_history()