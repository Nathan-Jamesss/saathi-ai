"""FastAPI auth dependencies"""
from typing import Optional

from fastapi import Depends, Header, HTTPException

from auth import firestore_repo
from auth.models import Role, User
from auth.security import decode_token


def _extract_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    return authorization.removeprefix("Bearer ").strip()


def get_optional_user(authorization: Optional[str] = Header(default=None)) -> Optional[User]:
    token = _extract_token(authorization)
    if not token:
        return None
    try:
        payload = decode_token(token)
    except Exception:
        return None
    user = firestore_repo.get_user(payload["sub"])
    if not user or not user.is_active:
        return None
    return user


def get_current_user(authorization: Optional[str] = Header(default=None)) -> User:
    token = _extract_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing token")
    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = firestore_repo.get_user(payload["sub"])
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user


def require_teacher(user: User = Depends(get_current_user)) -> User:
    if user.role != Role.teacher:
        raise HTTPException(status_code=403, detail="Teacher role required")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != Role.admin:
        raise HTTPException(status_code=403, detail="Admin role required")
    return user
