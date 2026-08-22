import time

import jwt
import pytest
from fastapi import HTTPException

from app.core.auth import get_user_id_from_header, require_user_id
from app.core.config import settings


def make_token(**overrides) -> str:
    claims = {
        "sub": "11111111-2222-3333-4444-555555555555",
        "aud": settings.supabase_jwt_audience,
        "exp": int(time.time()) + 3600,
    }
    claims.update(overrides)
    secret = overrides.pop("_secret", settings.supabase_jwt_secret)
    return jwt.encode(claims, secret, algorithm="HS256")


def test_absent_header_is_anonymous():
    assert get_user_id_from_header(None) is None


def test_valid_token_returns_subject():
    token = make_token()
    assert get_user_id_from_header(f"Bearer {token}") == "11111111-2222-3333-4444-555555555555"


def test_unsigned_token_is_rejected():
    """A token forged with a different key must never be accepted."""
    forged = jwt.encode(
        {"sub": "attacker", "aud": settings.supabase_jwt_audience, "exp": int(time.time()) + 3600},
        "not-the-real-secret",
        algorithm="HS256",
    )
    with pytest.raises(HTTPException) as exc:
        get_user_id_from_header(f"Bearer {forged}")
    assert exc.value.status_code == 401


def test_alg_none_token_is_rejected():
    forged = jwt.encode(
        {"sub": "attacker", "aud": settings.supabase_jwt_audience, "exp": int(time.time()) + 3600},
        key="",
        algorithm="none",
    )
    with pytest.raises(HTTPException) as exc:
        get_user_id_from_header(f"Bearer {forged}")
    assert exc.value.status_code == 401


def test_expired_token_is_rejected():
    token = make_token(exp=int(time.time()) - 10)
    with pytest.raises(HTTPException) as exc:
        get_user_id_from_header(f"Bearer {token}")
    assert exc.value.status_code == 401


def test_wrong_audience_is_rejected():
    token = make_token(aud="some-other-service")
    with pytest.raises(HTTPException) as exc:
        get_user_id_from_header(f"Bearer {token}")
    assert exc.value.status_code == 401


def test_malformed_header_is_rejected():
    with pytest.raises(HTTPException):
        get_user_id_from_header("Basic abc")
    with pytest.raises(HTTPException):
        get_user_id_from_header("Bearer ")


def test_require_user_id_rejects_anonymous():
    with pytest.raises(HTTPException) as exc:
        require_user_id(None)
    assert exc.value.status_code == 401
