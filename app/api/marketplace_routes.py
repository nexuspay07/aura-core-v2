from fastapi import APIRouter
from sqlalchemy import select

from app.db.database import SessionLocal
from app.models.strategy import strategies

router = APIRouter(
    prefix="/marketplace",
    tags=["Marketplace"]
)


# ==========================
# SAVE STRATEGY (NO AUTH)
# ==========================
@router.post("/save")
async def save_strategy(data: dict):

    db = SessionLocal()

    try:

        query = strategies.insert().values(
            name=data.get(
                "name",
                "Unnamed Strategy"
            ),
            goal=data.get("goal"),
            data=data,
            owner="guest",
            is_public=1
        )

        db.execute(query)
        db.commit()

    finally:

        db.close()

    return {
        "message":
        "Strategy saved to marketplace"
    }


# ==========================
# GET ALL PUBLIC STRATEGIES
# ==========================
@router.get("/all")
async def get_all():

    db = SessionLocal()

    try:

        query = (
            select(strategies)
            .where(
                strategies.c.is_public == 1
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


# ==========================
# GET MY STRATEGIES
# ==========================
@router.get("/mine")
async def get_my():

    db = SessionLocal()

    try:

        query = (
            select(strategies)
            .where(
                strategies.c.owner == "guest"
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


# ==========================
# GET SINGLE STRATEGY
# ==========================
@router.get("/{strategy_id}")
async def get_one(strategy_id: int):

    db = SessionLocal()

    try:

        query = (
            select(strategies)
            .where(
                strategies.c.id == strategy_id
            )
        )

        result = db.execute(query)

        row = result.fetchone()

    finally:

        db.close()

    if not row:

        return {
            "error":
            "Not found"
        }

    return dict(row._mapping)


# ==========================
# DELETE STRATEGY
# ==========================
@router.delete("/{strategy_id}")
async def delete(strategy_id: int):

    db = SessionLocal()

    try:

        query = (
            select(strategies)
            .where(
                strategies.c.id == strategy_id
            )
        )

        result = db.execute(query)

        strategy = result.fetchone()

        if not strategy:

            return {
                "error":
                "Not found"
            }

        delete_query = (
            strategies.delete()
            .where(
                strategies.c.id == strategy_id
            )
        )

        db.execute(delete_query)
        db.commit()

    finally:

        db.close()

    return {
        "message":
        "Deleted"
    }