from sqlalchemy.orm import Session

from app.models.user import User

from app.auth.password_handler import (
    hash_password,
    verify_password
)

from app.auth.jwt_handler import (
    create_access_token
)


class AuthService:

    # ==========================================
    # Register User
    # ==========================================

    def register(
        self,
        db: Session,
        first_name: str,
        last_name: str,
        email: str,
        password: str
    ):

        existing_user = (
            db.query(User)
            .filter(
                User.email == email
            )
            .first()
        )

        if existing_user:

            raise ValueError(
                "Email already exists."
            )

        user = User(

            first_name=first_name,

            last_name=last_name,

            email=email,

            password_hash=hash_password(
                password
            )
        )

        db.add(user)

        db.commit()

        db.refresh(user)

        return user

    # ==========================================
    # Login User
    # ==========================================

    def login(
        self,
        db: Session,
        email: str,
        password: str
    ):

        user = (
            db.query(User)
            .filter(
                User.email == email
            )
            .first()
        )

        if not user:

            raise ValueError(
                "Invalid email or password."
            )

        if not verify_password(
            password,
            user.password_hash
        ):

            raise ValueError(
                "Invalid email or password."
            )

        access_token = create_access_token(

            user_id=user.id,

            email=user.email
        )

        return {

            "user": user,

            "access_token": access_token,

            "token_type": "bearer"
        }

    # ==========================================
    # Get User
    # ==========================================

    def get_user_by_email(
        self,
        db: Session,
        email: str
    ):

        return (
            db.query(User)
            .filter(
                User.email == email
            )
            .first()
        )


auth_service = AuthService()