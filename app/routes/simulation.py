from fastapi import APIRouter
from sqlalchemy import select

from app.db.database import SessionLocal
from app.models.simulation import simulations

router = APIRouter()


# ==========================
# SAVE SIMULATION (NO AUTH)
# ==========================
@router.post("/simulation/save")
async def save_simulation(data: dict):

    db = SessionLocal()

    try:

        query = simulations.insert().values(
            goal=data.get("goal"),
            result=data,
            owner="guest"
        )

        db.execute(query)

        db.commit()

    finally:

        db.close()

    return {
        "message":
        "Simulation saved"
    }


# ==========================
# GET HISTORY (GLOBAL)
# ==========================
@router.get("/simulation/history")
async def get_history():

    db = SessionLocal()

    try:

        query = select(simulations)

        result = db.execute(query)

        rows = result.fetchall()

    finally:

        db.close()

    return [
        dict(row._mapping)
        for row in rows
    ]