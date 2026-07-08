from datetime import datetime, timedelta
from jose import jwt, JWTError

# ==========================================
# Configuration
# ==========================================

SECRET_KEY = "CHANGE_THIS_TO_A_LONG_RANDOM_SECRET"

ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_HOURS = 24


# ==========================================
# Create Access Token
# ==========================================

def create_access_token(
    user_id: int,
    email: str
):

    expire = (
        datetime.utcnow()
        + timedelta(
            hours=ACCESS_TOKEN_EXPIRE_HOURS
        )
    )

    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": expire
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


# ==========================================
# Verify Token
# ==========================================

def verify_access_token(
    token: str
):

    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        return payload

    except JWTError:

        return None