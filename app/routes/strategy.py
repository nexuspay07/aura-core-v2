from fastapi import (
    APIRouter,
    Depends
)

from sqlalchemy import (
    select
)

from app.db.database import (
    SessionLocal
)

from app.models.strategy import (
    strategies
)

from app.routes.auth import (
    get_current_user
)

router = APIRouter(
    prefix="/strategy",
    tags=["Strategy"]
)


# =============================
# SAVE STRATEGY
# =============================
@router.post("/save")
async def save_strategy(
    data: dict,
    user=Depends(get_current_user)
):

    strategy = data.get("strategy")

    db = SessionLocal()

    try:

        query = strategies.insert().values(
            name=strategy.get("name"),

            description=(
                f"Strategy for "
                f"{strategy.get('name')}"
            ),

            score=strategy.get(
                "final_score",
                strategy.get("score")
            ),

            owner=user["username"],

            data=strategy,

            votes=0
        )

        db.execute(query)

        db.commit()

    finally:

        db.close()

    return {
        "message":
        "Strategy saved"
    }


# =============================
# GET ALL STRATEGIES
# =============================
@router.get("/all")
async def get_all():

    db = SessionLocal()

    try:

        query = (
            select(strategies)
            .order_by(
                strategies.c.votes.desc()
            )
        )

        result = db.execute(query)

        rows = result.fetchall()

    finally:

        db.close()

    return [
        dict(row._mapping)
        for row in rows
    ]


# =============================
# GET MY STRATEGIES
# =============================
@router.get("/my")
async def get_my(
    user=Depends(get_current_user)
):

    db = SessionLocal()

    try:

        query = (
            select(strategies)
            .where(
                strategies.c.owner
                == user["username"]
            )
        )

        result = db.execute(query)

        rows = result.fetchall()

    finally:

        db.close()

    return [
        dict(row._mapping)
        for row in rows
    ]


# =============================
# UPVOTE STRATEGY
# =============================
@router.post("/vote/{strategy_id}")
async def vote(strategy_id: int):

    db = SessionLocal()

    try:

        query = (
            strategies.update()
            .where(
                strategies.c.id
                == strategy_id
            )
            .values(
                votes=(
                    strategies.c.votes + 1
                )
            )
        )

        db.execute(query)

        db.commit()

    finally:

        db.close()

    return {
        "message":
        "Voted"
    }