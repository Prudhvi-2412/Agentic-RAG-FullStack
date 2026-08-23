import logging
import threading
from typing import Optional

import jwt
from fastapi import Header, HTTPException

from app.core.config import settings

logger = logging.getLogger(__name__)

# Vectors that belong to no single user: the pre-indexed demo document that every visitor
# (signed in or not) is allowed to read, and that nobody is allowed to delete.
SHARED_DOCUMENT_IDS = ["ikigai-default-doc-id"]

# Supabase signs access tokens with either the legacy shared HS256 secret or a per-project
# asymmetric key. Only these algorithms are ever accepted — notably never "none".
_SYMMETRIC_ALGORITHMS = {"HS256"}
_ASYMMETRIC_ALGORITHMS = {"ES256", "RS256"}

_jwk_client = None
_jwk_client_lock = threading.Lock()


def _get_jwk_client():
    """Lazily builds a JWKS client. PyJWKClient caches fetched keys internally."""
    global _jwk_client
    if _jwk_client is None:
        with _jwk_client_lock:
            if _jwk_client is None:
                _jwk_client = jwt.PyJWKClient(settings.supabase_jwks_url, cache_keys=True)
    return _jwk_client


def _signing_key_for(token: str, algorithm: str):
    """
    Resolves the verification key for a token's algorithm.

    The algorithm is read from the (unverified) header only to choose a key *source*, and each
    source is bound to one algorithm family: HS256 always uses the configured shared secret and
    never a key from the JWKS. That closes the classic algorithm-confusion attack, where a
    published public key is replayed as an HMAC secret.
    """
    if algorithm in _SYMMETRIC_ALGORITHMS:
        if not settings.supabase_jwt_secret:
            raise jwt.InvalidTokenError(
                "Token is HS256-signed but SUPABASE_JWT_SECRET is not configured"
            )
        return settings.supabase_jwt_secret

    if algorithm in _ASYMMETRIC_ALGORITHMS:
        if not settings.supabase_jwks_url:
            raise jwt.InvalidTokenError(
                f"Token is {algorithm}-signed but SUPABASE_URL is not configured"
            )
        return _get_jwk_client().get_signing_key_from_jwt(token).key

    raise jwt.InvalidTokenError(f"Unsupported token algorithm: {algorithm!r}")


def _decode(token: str) -> dict:
    algorithm = jwt.get_unverified_header(token).get("alg")
    key = _signing_key_for(token, algorithm)
    return jwt.decode(
        token,
        key,
        algorithms=[algorithm],
        audience=settings.supabase_jwt_audience,
        options={"require": ["exp", "sub"]},
    )


def get_user_id_from_header(authorization: Optional[str] = Header(None)) -> Optional[str]:
    """
    Verifies the Supabase access token's signature and expiry and returns the user's UUID.

    Returns None when no Authorization header is supplied (anonymous access, which callers
    restrict to shared demo content). Raises 401 when a token is supplied but is not valid —
    an unverifiable token must never be silently downgraded to anonymous access.
    """
    if not authorization:
        return None

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization header format.")

    token = authorization[7:].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Invalid Authorization header format.")

    try:
        claims = _decode(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired. Please sign in again.")
    except jwt.PyJWKClientConnectionError as exc:
        # The JWKS endpoint is unreachable: the token may well be valid, so telling the user
        # to sign in again would be wrong. This is a server-side outage.
        logger.error("Could not reach the Supabase JWKS endpoint: %s", exc)
        raise HTTPException(status_code=503, detail="Authentication is temporarily unavailable.")
    except jwt.PyJWTError as exc:
        # Covers invalid signatures, bad claims, and unresolvable signing keys.
        logger.warning("Rejected access token: %s", exc)
        raise HTTPException(status_code=401, detail="Invalid authentication token.")

    subject = claims.get("sub")
    if not subject:
        raise HTTPException(status_code=401, detail="Invalid authentication token.")

    return str(subject)


def require_user_id(authorization: Optional[str] = Header(None)) -> str:
    """FastAPI dependency for endpoints that operate on user-owned resources."""
    user_id = get_user_id_from_header(authorization)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required. Please sign in.")
    return user_id
