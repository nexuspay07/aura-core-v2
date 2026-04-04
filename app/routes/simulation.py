from fastapi import APIRouter
from app.db.database import database
from app.models.simulation import simulations

router = APIRouter()


# ==========================
# SAVE SIMULATION (NO AUTH)
# ==========================
@router.post("/simulation/save")
async def save_simulation(data: dict):
    await database.execute(
        simulations.insert().values(
            goal=data.get("goal"),
            result=data,
            owner="guest"  # ✅ fallback user
        )
    )
    return {"message": "Simulation saved"}


# ==========================
# GET HISTORY (GLOBAL)
# ==========================
@router.get("/simulation/history")
async def get_history():
    query = simulations.select()  # ✅ no filtering
    return await database.fetch_all(query)