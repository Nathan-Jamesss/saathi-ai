import time

import jwt
import pytest

from auth.security import (
    hash_password,
    verify_password,
    create_token,
    decode_token,
    JWT_SECRET,
    JWT_ALGORITHM,
)


def test_hash_and_verify_roundtrip():
    hashed = hash_password("s3cret!")
    assert hashed != "s3cret!"
    assert verify_password("s3cret!", hashed) is True
    assert verify_password("wrong", hashed) is False


def test_create_and_decode_token():
    token = create_token(user_id=42, role="teacher")
    payload = decode_token(token)
    assert payload["sub"] == "42"
    assert payload["role"] == "teacher"


def test_decode_rejects_expired_token():
    expired = jwt.encode(
        {"sub": "1", "role": "teacher", "exp": int(time.time()) - 10},
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_token(expired)
