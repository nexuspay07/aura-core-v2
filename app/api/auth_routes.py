from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, insert
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.db.database import database
from app.db.user_table import user_table
from app.core.auth_engine import auth_engine


router = APIRouter(prefix="/auth", tags=["Auth"])
security = HTTPBearer()


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


def clean_user(row):
    return {
        "id": row["id"],
        "email": row["email"],
        "full_name": row["full_name"],
        "role": row["role"],
        "is_active": row["is_active"],
        "is_verified": row["is_verified"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
    }


async def get_current_user_from_token(
    credentials: HTTPAuthorizationCredentials
):
    token = credentials.credentials

    payload = auth_engine.decode_token(token)

    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )

    user_id = int(payload["sub"])

    query = select(user_table).where(
        user_table.c.id == user_id
    )

    user = await database.fetch_one(query)

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    return {
        "id": user["id"],
        "email": user["email"],
        "full_name": user["full_name"],
        "role": user["role"]
    }


@router.post("/register")
async def register(data: RegisterRequest):
    if len(data.password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters"
        )

    existing_query = select(user_table).where(user_table.c.email == data.email.lower())
    existing_user = await database.fetch_one(existing_query)

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    password_hash = auth_engine.hash_password(data.password)

    query = insert(user_table).values(
        email=data.email.lower(),
        password_hash=password_hash,
        full_name=data.full_name,
        role="user",
        is_active=True,
        is_verified=False,
    )

    user_id = await database.execute(query)

    token = auth_engine.create_access_token(
        user_id=user_id,
        email=data.email.lower(),
        role="user"
    )

    return {
        "success": True,
        "message": "Account created successfully",
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user_id,
            "email": data.email.lower(),
            "full_name": data.full_name,
            "role": "user",
            "is_active": True,
            "is_verified": False,
        }
    }


@router.post("/login")
async def login(data: LoginRequest):
    query = select(user_table).where(user_table.c.email == data.email.lower())
    user = await database.fetch_one(query)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not auth_engine.verify_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user["is_active"]:
        raise HTTPException(status_code=403, detail="User account is disabled")

    token = auth_engine.create_access_token(
        user_id=user["id"],
        email=user["email"],
        role=user["role"]
    )

    return {
        "success": True,
        "message": "Login successful",
        "access_token": token,
        "token_type": "bearer",
        "user": clean_user(user)
    }


@router.get("/me")
async def me(authorization: str | None = Header(default=None)):
    user = await get_current_user_from_token(authorization)

    return {
        "success": True,
        "user": clean_user(user)
    }