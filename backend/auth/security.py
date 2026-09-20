"""Password hashing & JWT issuance/verification"""
import os
import time

import jwt
from passlib.context import CryptContext

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret-change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_SECONDS = 24 * 60 * 60


def hash_password(password: str) -> str:
    return _pwd_ctx.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _pwd_ctx.verify(password, password_hash)


def create_token(user_id: int, role: str) -> str:
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": int(time.time()) + JWT_EXPIRY_SECONDS,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
