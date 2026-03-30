from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from app.db.database import database
from app.models.user import users
from pydantic import BaseModel
from jose import jwt, JWTError
from datetime import datetime, timedelta
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
import os

router = APIRouter()

# ==========================
# SECURITY CONFIG
# ==========================
SECRET_KEY = os.getenv("SECRET_KEY", "dev_secret_change_this")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 2

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

security = HTTPBearer()

# ==========================
# MODELS
# ==========================
class AuthRequest(BaseModel):
    username: str
    password: str


# ==========================
# PASSWORD HELPERS
# ==========================
def hash_password(password: str):
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)


# ==========================
# TOKEN CREATION
# ==========================
def create_token(username: str):
    payload = {
        "sub": username,
        "exp": datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# ==========================
# ✅ PREFLIGHT HANDLER (CRITICAL FIX)
# ==========================
# ==========================
# REGISTER
# ==========================
@router.post("/register")
async def register(data: AuthRequest):
    if not data.username or not data.password:
        raise HTTPException(status_code=400, detail="Missing credentials")

    existing = await database.fetch_one(
        users.select().where(users.c.username == data.username)
    )

    if existing:
        raise HTTPException(status_code=400, detail="User already exists")

    hashed = hash_password(data.password)

    await database.execute(
        users.insert().values(
            username=data.username,
            password=hashed
        )
    )

    return {"message": "User created successfully"}


# ==========================
# LOGIN
# ==========================
@router.post("/login")
async def login(data: AuthRequest):
    user = await database.fetch_one(
        users.select().where(users.c.username == data.username)
    )

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_token(user["username"])

    return {
        "access_token": token,
        "token_type": "bearer"
    }


# ==========================
# CURRENT USER (PROTECTED)
# ==========================
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")

        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        return {"username": username}

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")