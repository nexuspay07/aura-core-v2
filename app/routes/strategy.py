from fastapi import APIRouter, Depends
from app.db.database import database
from app.models.strategy import strategies
from app.routes.auth import get_current_user

router = APIRouter(prefix="/strategy", tags=["Strategy"])

# =============================
# SAVE STRATEGY
# =============================
@router.post("/save")
async def save_strategy(data: dict, user=Depends(get_current_user)):
    strategy = data.get("strategy")

    query = strategies.insert().values(
        name=strategy.get("name"),
        description=f"Strategy for {strategy.get('name')}",
        score=strategy.get("final_score", strategy.get("score")),
        owner=user["username"],
        data=strategy,
        votes=0
    )

    await database.execute(query)

    return {"message": "Strategy saved"}

# =============================
# GET ALL STRATEGIES
# =============================
@router.get("/all")
async def get_all():
    query = strategies.select().order_by(strategies.c.votes.desc())
    return await database.fetch_all(query)

# =============================
# GET MY STRATEGIES
# =============================
@router.get("/my")
async def get_my(user=Depends(get_current_user)):
    query = strategies.select().where(
        strategies.c.owner == user["username"]
    )
    return await database.fetch_all(query)

# =============================
# UPVOTE STRATEGY
# =============================
@router.post("/vote/{strategy_id}")
async def vote(strategy_id: int):
    query = strategies.update().where(
        strategies.c.id == strategy_id
    ).values(
        votes=strategies.c.votes + 1
    )

    await database.execute(query)

    return {"message": "Voted"}