"""FastAPI auth dependencies"""
from typing import Optional

from fastapi import Depends, Header, HTTPException
from sqlmodel import Session

from db import get_db
from auth.models import Role, User
from auth.security import decode_token


def _extract_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    return authorization.removeprefix("Bearer ").strip()


def get_optional_user(
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> Optional[User]:
    token = _extract_token(authorization)
    if not token:
        return None
    try:
        payload = decode_token(token)
    except Exception:
        return None
    user = db.get(User, int(payload["sub"]))
    if not user or not user.is_active:
        return None
    return user


def get_current_user(
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    token = _extract_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Missing token")
    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = db.get(User, int(payload["sub"]))
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
