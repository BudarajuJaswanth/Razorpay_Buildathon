import os
import time
from typing import Optional
import jwt

JWT_SECRET = os.getenv("JWT_SECRET", "kicksvault-super-secret-key-2026-buildathon-secured")
JWT_ALGORITHM = "HS256"

def create_jwt_token(payload: dict, expires_in_seconds: int = 3600) -> str:
    """
    Creates a cryptographically signed HS256 JWT token with a 1-hour expiration timestamp.
    """
    data = payload.copy()
    now = int(time.time())
    if "exp" not in data:
        data["exp"] = now + expires_in_seconds
    if "iat" not in data:
        data["iat"] = now
    return jwt.encode(data, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_jwt_token(token: str) -> Optional[dict]:
    """
    Verifies a signed HS256 JWT token and returns the payload if valid and not expired.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, Exception):
        return None
