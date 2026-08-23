"""
Covers Supabase projects that sign access tokens with asymmetric keys (ES256/RS256) rather
than the legacy shared HS256 secret, plus the algorithm-confusion defence between the two.
"""

import base64
import hashlib
import hmac
import json
import time
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import HTTPException

from app.core import auth
from app.core.config import settings


@pytest.fixture
def ec_key():
    return ec.generate_private_key(ec.SECP256R1())


@pytest.fixture
def jwks_backed(monkeypatch, ec_key):
    """Points the JWKS client at a locally generated key instead of the network."""
    monkeypatch.setattr(auth, "_jwk_client", None, raising=False)
    monkeypatch.setattr(
        auth,
        "_get_jwk_client",
        lambda: SimpleNamespace(
            get_signing_key_from_jwt=lambda token: SimpleNamespace(key=ec_key.public_key())
        ),
    )
    monkeypatch.setattr(type(settings), "supabase_jwks_url",
                        property(lambda self: "https://example.supabase.co/auth/v1/.well-known/jwks.json"))
    yield


def es256_token(key, **overrides):
    claims = {
        "sub": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "aud": settings.supabase_jwt_audience,
        "exp": int(time.time()) + 3600,
    }
    claims.update(overrides)
    return jwt.encode(claims, key, algorithm="ES256")


def test_es256_token_is_accepted_via_jwks(jwks_backed, ec_key):
    token = es256_token(ec_key)
    assert auth.get_user_id_from_header(f"Bearer {token}") == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


def test_es256_token_signed_by_a_different_key_is_rejected(jwks_backed):
    attacker_key = ec.generate_private_key(ec.SECP256R1())
    token = es256_token(attacker_key)
    with pytest.raises(HTTPException) as exc:
        auth.get_user_id_from_header(f"Bearer {token}")
    assert exc.value.status_code == 401


def test_expired_es256_token_is_rejected(jwks_backed, ec_key):
    token = es256_token(ec_key, exp=int(time.time()) - 10)
    with pytest.raises(HTTPException) as exc:
        auth.get_user_id_from_header(f"Bearer {token}")
    assert exc.value.status_code == 401


def test_jwks_outage_reports_unavailable_not_unauthorized(monkeypatch, ec_key):
    """A token may be perfectly valid; an unreachable JWKS endpoint is our problem, not the user's."""
    monkeypatch.setattr(type(settings), "supabase_jwks_url",
                        property(lambda self: "https://example.supabase.co/auth/v1/.well-known/jwks.json"))

    def boom():
        raise jwt.PyJWKClientConnectionError("cannot reach jwks")

    monkeypatch.setattr(auth, "_get_jwk_client", boom)
    token = es256_token(ec_key)
    with pytest.raises(HTTPException) as exc:
        auth.get_user_id_from_header(f"Bearer {token}")
    assert exc.value.status_code == 503


def test_public_key_cannot_be_replayed_as_an_hmac_secret(jwks_backed, ec_key):
    """
    Algorithm confusion: an attacker takes the project's public JWK, signs an HS256 token with
    it, and hopes the server verifies HS256 using that same key. HS256 must only ever use the
    configured shared secret.

    The token is assembled by hand because PyJWT's encoder refuses to HMAC-sign with a public
    key — the point here is to test our verification path, not PyJWT's encoder.
    """
    public_pem = ec_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    def b64(raw: bytes) -> bytes:
        return base64.urlsafe_b64encode(raw).rstrip(b"=")

    header = b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = b64(json.dumps({
        "sub": "attacker",
        "aud": settings.supabase_jwt_audience,
        "exp": int(time.time()) + 3600,
    }).encode())
    signing_input = header + b"." + payload
    signature = b64(hmac.new(public_pem, signing_input, hashlib.sha256).digest())
    forged = (signing_input + b"." + signature).decode()

    with pytest.raises(HTTPException) as exc:
        auth.get_user_id_from_header(f"Bearer {forged}")
    assert exc.value.status_code == 401


def test_unsupported_algorithm_is_rejected(jwks_backed):
    forged = jwt.encode(
        {"sub": "attacker", "aud": settings.supabase_jwt_audience, "exp": int(time.time()) + 3600},
        key="",
        algorithm="none",
    )
    with pytest.raises(HTTPException) as exc:
        auth.get_user_id_from_header(f"Bearer {forged}")
    assert exc.value.status_code == 401


def test_hs256_token_rejected_when_only_jwks_is_configured(monkeypatch, jwks_backed):
    monkeypatch.setattr(settings, "supabase_jwt_secret", None)
    token = jwt.encode(
        {"sub": "user", "aud": settings.supabase_jwt_audience, "exp": int(time.time()) + 3600},
        "some-secret",
        algorithm="HS256",
    )
    with pytest.raises(HTTPException) as exc:
        auth.get_user_id_from_header(f"Bearer {token}")
    assert exc.value.status_code == 401


def test_config_requires_at_least_one_verification_method():
    from app.core.config import Settings

    with pytest.raises(Exception) as exc:
        Settings(
            _env_file=None,
            gemini_api_key="x",
            pinecone_api_key="y",
            supabase_jwt_secret=None,
            supabase_url=None,
        )
    assert "SUPABASE_JWT_SECRET" in str(exc.value)


def test_config_accepts_jwks_only_configuration():
    from app.core.config import Settings

    s = Settings(
        _env_file=None,
        gemini_api_key="x",
        pinecone_api_key="y",
        supabase_url="https://abc.supabase.co/",
    )
    assert s.supabase_jwks_url == "https://abc.supabase.co/auth/v1/.well-known/jwks.json"
