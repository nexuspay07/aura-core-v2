from fastapi import APIRouter
from app.db.database import database
from app.models.strategy import strategies

router = APIRouter(prefix="/marketplace", tags=["Marketplace"])


# ==========================
# SAVE STRATEGY (NO AUTH)
# ==========================
@router.post("/save")
async def save_strategy(data: dict):
    await database.execute(
        strategies.insert().values(
            name=data.get("name", "Unnamed Strategy"),
            goal=data.get("goal"),
            data=data,
            owner="guest",   # ✅ fallback user
            is_public=1
        )
    )
    return {"message": "Strategy saved to marketplace"}


# ==========================
# GET ALL PUBLIC STRATEGIES
# ==========================
@router.get("/all")
async def get_all():
    query = strategies.select().where(strategies.c.is_public == 1)
    return await database.fetch_all(query)


# ==========================
# GET MY STRATEGIES (NOW = ALL GUEST)
# ==========================
@router.get("/mine")
async def get_my():
    query = strategies.select().where(
        strategies.c.owner == "guest"
    )
    return await database.fetch_all(query)


# ==========================
# GET SINGLE STRATEGY
# ==========================
@router.get("/{strategy_id}")
async def get_one(strategy_id: int):
    query = strategies.select().where(strategies.c.id == strategy_id)
    return await database.fetch_one(query)


# ==========================
# DELETE STRATEGY (NO AUTH CHECK)
# ==========================
@router.delete("/{strategy_id}")
async def delete(strategy_id: int):
    query = strategies.select().where(strategies.c.id == strategy_id)
    strategy = await database.fetch_one(query)

    if not strategy:
        return {"error": "Not found"}

    # ✅ No ownership check (open system)
    await database.execute(
        strategies.delete().where(strategies.c.id == strategy_id)
    )

    return {"message": "Deleted"}