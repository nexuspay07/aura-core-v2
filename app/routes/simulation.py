from fastapi import APIRouter, Depends
from app.db.database import database
from app.models.simulation import simulations
from app.routes.auth import get_current_user

router = APIRouter()


# ✅ SAVE SIMULATION
@router.post("/simulation/save")
async def save_simulation(data: dict, user=Depends(get_current_user)):
    await database.execute(
        simulations.insert().values(
            goal=data.get("goal"),
            result=data,
            owner=user["username"]
        )
    )
    return {"message": "Simulation saved"}


# ✅ GET USER HISTORY  ← STEP 8 HERE
@router.get("/simulation/history")
async def get_history(user=Depends(get_current_user)):
    query = simulations.select().where(
        simulations.c.owner == user["username"]
    )

    return await database.fetch_all(query)