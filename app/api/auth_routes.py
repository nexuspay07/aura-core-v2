from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select, insert, update
from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.db.database import SessionLocal
from app.db.user_table import user_table
from app.db.password_reset_token_table import password_reset_token_table
from app.core.auth_engine import auth_engine
from app.services.identity_service import (
    identity_service
)
from app.services.onboarding_service import (
    onboarding_service
)
from app.core.rate_limit import FixedWindowRateLimiter, RateLimitPolicy
from app.services.password_reset_mailer import configured_password_reset_mailer, log_password_reset_stage, password_reset_url


router = APIRouter(prefix="/auth", tags=["Auth"])
security = HTTPBearer()


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None
    account_type: str = "business"
    organization_name: str | None = Field(default=None, min_length=2, max_length=255)
    industry: str | None = Field(default=None, max_length=100)
    company_size: str | None = Field(default=None, max_length=50)
    workspace_name: str | None = Field(default=None, min_length=2, max_length=255)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str = Field(min_length=32, max_length=512)
    password: str = Field(min_length=8, max_length=256)


PASSWORD_RESET_MESSAGE = "If an account exists for that email, the password reset request has been accepted."


password_reset_limiter = FixedWindowRateLimiter()
password_reset_policy = RateLimitPolicy(limit=3, window_seconds=900)

def deliver_password_reset(email: str, token: str) -> bool:
    try:
        return configured_password_reset_mailer().send(email, password_reset_url(token))
    except Exception:
        log_password_reset_stage("transport_error")
        return False


def clean_user(row):

    if hasattr(row, "_mapping"):
        row = dict(row._mapping)

    return {
        "id": row["id"],
        "email": row["email"],
        "full_name": row["full_name"],
        "role": row["role"],
        "is_active": row["is_active"],
        "is_verified": row["is_verified"],
        "active_workspace_id": row.get("active_workspace_id"),
        "created_at": (
            row["created_at"].isoformat()
            if row["created_at"]
            else None
        ),
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

    db = SessionLocal()

    try:

        query = select(user_table).where(
            user_table.c.id == user_id
        )

        result = db.execute(query)

        user = result.fetchone()

        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        user = dict(user._mapping)

        identity = identity_service.resolve(

            db=db,

            user_id=user["id"]

        )

        return identity

    finally:

        db.close()


def _validate_account_type(account_type: str) -> str:
    if account_type not in {"personal", "business", "enterprise"}:
        raise HTTPException(status_code=422, detail="Unsupported account type")
    return account_type

@router.post("/register")
async def register(data: RegisterRequest):

    if len(data.password) < 8:

        raise HTTPException(

            status_code=400,

            detail="Password must be at least 8 characters"

        )

    account_type = _validate_account_type(data.account_type)
    db = SessionLocal()

    try:

        existing_query = select(user_table).where(

            user_table.c.email == data.email.lower()

        )

        existing_result = db.execute(existing_query)

        existing_user = existing_result.fetchone()

        if existing_user:

            raise HTTPException(

                status_code=400,

                detail="Email already registered"

            )

        password_hash = auth_engine.hash_password(

            data.password

        )

        query = insert(user_table).values(

            email=data.email.lower(),

            password_hash=password_hash,

            full_name=data.full_name,

            role="user",

            is_active=True,

            is_verified=False,

        )

        result = db.execute(query)

        user_id = result.inserted_primary_key[0]

        onboarding_service.initialize(

            db=db,

            user_id=user_id,

            full_name=data.full_name,
            account_type=account_type,
            organization_name=data.organization_name,
            industry=data.industry,
            company_size=data.company_size,
            workspace_name=data.workspace_name,

        )

        db.commit()

    except Exception:

        db.rollback()

        raise

    finally:

        db.close()

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

            "is_verified": False

        }

    }


class ActiveWorkspaceRequest(BaseModel):
    workspace_id: int


@router.post("/context/workspace")
async def select_active_workspace(
    data: ActiveWorkspaceRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    token = credentials.credentials
    payload = auth_engine.decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    db = SessionLocal()
    try:
        user_id = int(payload["sub"])
        if identity_service._accessible_context(db, user_id, data.workspace_id) is None:
            raise HTTPException(status_code=404, detail="Workspace not found")
        db.execute(
            update(user_table)
            .where(user_table.c.id == user_id)
            .values(active_workspace_id=data.workspace_id)
        )
        db.commit()
        return {"success": True, "identity": identity_service.resolve(db, user_id=user_id)}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()



@router.post("/login")
async def login(data: LoginRequest):

    db = SessionLocal()

    try:

        query = select(user_table).where(

            user_table.c.email == data.email.lower()

        )

        result = db.execute(query)

        user = result.fetchone()

        if not user:

            raise HTTPException(

                status_code=401,

                detail="Invalid email or password"

            )

        user = dict(user._mapping)

        if not auth_engine.verify_password(

            data.password,

            user["password_hash"]

        ):

            raise HTTPException(

                status_code=401,

                detail="Invalid email or password"

            )

        if not user["is_active"]:

            raise HTTPException(

                status_code=403,

                detail="User account is disabled"

            )

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

    finally:

        db.close()


@router.post("/password-reset/request")
async def request_password_reset(data: PasswordResetRequest):
    db = SessionLocal()
    try:
        email=data.email.lower()
        allowed=password_reset_limiter.allow(("password_reset",hashlib.sha256(email.encode()).hexdigest()),password_reset_policy)
        user = db.execute(select(user_table).where(user_table.c.email == email)).mappings().first()
        if not allowed:
            log_password_reset_stage("rate_limited")
        elif not user or not user["is_active"]:
            log_password_reset_stage("account_ineligible")
        else:
            now = datetime.now(timezone.utc)
            recent = db.execute(
                select(func.count()).select_from(password_reset_token_table).where(
                    password_reset_token_table.c.user_id == user["id"],
                    password_reset_token_table.c.created_at >= now - timedelta(minutes=15),
                )
            ).scalar_one()
            if recent >= 3:
                log_password_reset_stage("recent_token_limited")
            else:
                token = secrets.token_urlsafe(48)
                db.execute(update(password_reset_token_table).where(password_reset_token_table.c.user_id==user["id"],password_reset_token_table.c.used_at.is_(None)).values(used_at=now))
                db.execute(insert(password_reset_token_table).values(
                    user_id=user["id"], token_hash=hashlib.sha256(token.encode()).hexdigest(),
                    expires_at=now + timedelta(minutes=30), created_at=now,
                ))
                db.commit()
                deliver_password_reset(user["email"], token)
        return {"message": PASSWORD_RESET_MESSAGE}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@router.post("/password-reset/confirm")
async def confirm_password_reset(data: PasswordResetConfirm):
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        token_hash = hashlib.sha256(data.token.encode()).hexdigest()
        record = db.execute(
            select(password_reset_token_table).where(
                password_reset_token_table.c.token_hash == token_hash,
                password_reset_token_table.c.used_at.is_(None),
                password_reset_token_table.c.expires_at > now,
            )
        ).mappings().first()
        if not record:
            raise HTTPException(status_code=400, detail="Reset link is invalid or expired")
        claimed=db.execute(update(password_reset_token_table).where(
            password_reset_token_table.c.id == record["id"],
            password_reset_token_table.c.used_at.is_(None),
            password_reset_token_table.c.expires_at > now,
        ).values(used_at=now))
        if claimed.rowcount != 1: raise HTTPException(status_code=400, detail="Reset link is invalid or expired")
        db.execute(update(user_table).where(user_table.c.id == record["user_id"]).values(password_hash=auth_engine.hash_password(data.password),updated_at=now))
        db.commit()
        return {"message": "Password reset complete. You can now sign in."}
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

@router.get("/me")
async def me(

    credentials: HTTPAuthorizationCredentials = Depends(security)

):

    identity = await get_current_user_from_token(

        credentials

    )

    return {"success": True, "identity": identity, **identity}
