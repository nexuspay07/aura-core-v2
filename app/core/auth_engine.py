import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import jwt, JWTError
from passlib.context import CryptContext


class AuthEngine:

    def __init__(self):

        self.secret_key = os.getenv(
            "JWT_SECRET_KEY",
            "CHANGE_THIS_SECRET_KEY"
        )
        if self.secret_key.startswith("CHANGE_THIS") and os.getenv("ENVIRONMENT", "development") == "production":
            raise RuntimeError("JWT_SECRET_KEY must be configured in production.")
        self.logger = logging.getLogger("aura.auth")

        self.algorithm = os.getenv(
            "JWT_ALGORITHM",
            "HS256"
        )

        self.access_token_expire_minutes = int(
            os.getenv(
                "ACCESS_TOKEN_EXPIRE_MINUTES",
                "1440"
            )
        )

        self.password_context = CryptContext(
            schemes=["bcrypt"],
            deprecated="auto"
        )

    # =====================================================
    # PASSWORDS
    # =====================================================

    def hash_password(self, password: str) -> str:

        return self.password_context.hash(password)

    def verify_password(
        self,
        plain_password: str,
        password_hash: str
    ) -> bool:

        return self.password_context.verify(
            plain_password,
            password_hash
        )

    # =====================================================
    # CREATE JWT
    # =====================================================

    def create_access_token(

        self,

        user_id: int,

        email: str,

        role: str = "user"

    ) -> str:

        expire = datetime.now(
            timezone.utc
        ) + timedelta(

            minutes=self.access_token_expire_minutes

        )

        payload = {

            "sub": str(user_id),

            "email": email,

            "role": role,

            "exp": expire

        }

        token = jwt.encode(

            payload,

            self.secret_key,

            algorithm=self.algorithm

        )

        self.logger.info("Issued access token for user_id=%s", user_id)

        return token

    # =====================================================
    # DECODE JWT
    # =====================================================

    def decode_token(
        self,
        token: str
    ) -> Optional[dict]:

        try:

            payload = jwt.decode(

                token,

                self.secret_key,

                algorithms=[self.algorithm]

            )

            return payload

        except JWTError:
            self.logger.info("Rejected invalid or expired access token")
            return None

        except Exception:
            self.logger.exception("Unexpected token decoding failure")
            return None


auth_engine = AuthEngine()
