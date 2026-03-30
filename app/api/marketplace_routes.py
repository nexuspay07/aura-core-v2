from fastapi import APIRouter, Depends
from app.db.database import database
from app.models.strategy import strategies
from app.routes.auth import get_current_user

router = APIRouter(prefix="/marketplace", tags=["Marketplace"])


# ==========================
# SAVE STRATEGY
# ==========================
@router.post("/save")
async def save_strategy(data: dict, user=Depends(get_current_user)):
    await database.execute(
        strategies.insert().values(
            name=data.get("name", "Unnamed Strategy"),
            goal=data.get("goal"),
            data=data,
            owner=user["username"],
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
# GET MY STRATEGIES
# ==========================
@router.get("/mine")
async def get_my(user=Depends(get_current_user)):
    query = strategies.select().where(
        strategies.c.owner == user["username"]
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
# DELETE STRATEGY
# ==========================
@router.delete("/{strategy_id}")
async def delete(strategy_id: int, user=Depends(get_current_user)):
    query = strategies.select().where(strategies.c.id == strategy_id)
    strategy = await database.fetch_one(query)

    if not strategy:
        return {"error": "Not found"}

    if strategy["owner"] != user["username"]:
        return {"error": "Unauthorized"}

    await database.execute(
        strategies.delete().where(strategies.c.id == strategy_id)
    )

    return {"message": "Deleted"}