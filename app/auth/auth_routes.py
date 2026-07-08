from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Header
)

from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.database import get_db

from app.auth.auth_service import (
    auth_service
)

from app.auth.jwt_handler import (
    verify_access_token
)

from app.models.user import User


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


# ==========================================
# Request Models
# ==========================================

class RegisterRequest(BaseModel):

    first_name: str

    last_name: str

    email: str

    password: str


class LoginRequest(BaseModel):

    email: str

    password: str


# ==========================================
# Register
# ==========================================

@router.post("/register")

def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):

    try:

        user = auth_service.register(

            db=db,

            first_name=request.first_name,

            last_name=request.last_name,

            email=request.email,

            password=request.password

        )

        return {

            "success": True,

            "message": "Registration successful.",

            "user": {

                "id": user.id,

                "first_name": user.first_name,

                "last_name": user.last_name,

                "email": user.email

            }

        }

    except ValueError as e:

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )


# ==========================================
# Login
# ==========================================

@router.post("/login")

def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):

    try:

        result = auth_service.login(

            db=db,

            email=request.email,

            password=request.password

        )

        return {

            "success": True,

            "access_token": result["access_token"],

            "token_type": result["token_type"],

            "user": {

                "id": result["user"].id,

                "first_name": result["user"].first_name,

                "last_name": result["user"].last_name,

                "email": result["user"].email

            }

        }

    except ValueError as e:

        raise HTTPException(
            status_code=401,
            detail=str(e)
        )


# ==========================================
# Current User
# ==========================================

@router.get("/me")

def me(

    authorization: str = Header(...),

    db: Session = Depends(get_db)

):

    try:

        token = authorization.replace(
            "Bearer ",
            ""
        )

        payload = verify_access_token(
            token
        )

        if payload is None:

            raise HTTPException(
                status_code=401,
                detail="Invalid token."
            )

        user = auth_service.get_user_by_email(

            db,

            payload["email"]

        )

        if user is None:

            raise HTTPException(
                status_code=404,
                detail="User not found."
            )

        return {

            "success": True,

            "user": {

                "id": user.id,

                "first_name": user.first_name,

                "last_name": user.last_name,

                "email": user.email,

                "is_active": user.is_active,

                "is_verified": user.is_verified

            }

        }

    except Exception:

        raise HTTPException(
            status_code=401,
            detail="Unauthorized."
        )