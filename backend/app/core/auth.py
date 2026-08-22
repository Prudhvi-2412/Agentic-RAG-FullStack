import logging
from typing import Optional

import jwt
from fastapi import Header, HTTPException

from app.core.config import settings

logger = logging.getLogger(__name__)

# Vectors that belong to no single user: the pre-indexed demo document that every visitor
# (signed in or not) is allowed to read, and that nobody is allowed to delete.
SHARED_DOCUMENT_IDS = ["ikigai-default-doc-id"]


def _decode(token: str) -> dict:
    return jwt.decode(
        token,
        settings.supabase_jwt_secret,
        algorithms=["HS256"],
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
    except jwt.InvalidTokenError as exc:
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
