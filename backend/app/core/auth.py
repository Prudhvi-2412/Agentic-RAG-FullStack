import json
import base64
from fastapi import Request, Header, HTTPException
from typing import Optional

def get_user_id_from_header(authorization: Optional[str] = Header(None)) -> Optional[str]:
    """
    Parses and decodes the JWT Authorization token to extract the user's Supabase UUID.
    This does base64 decoding of the payload. Signature validation is performed by the frontend/gateway,
    allowing the backend to remain lightweight and stateless.
    """
    if not authorization:
        return None
        
    if not authorization.startswith("Bearer "):
        return None
        
    token = authorization[7:]
    try:
        parts = token.split(".")
        if len(parts) == 3:
            payload = parts[1]
            # Fix base64 padding
            payload += "=" * ((4 - len(payload) % 4) % 4)
            decoded = base64.b64decode(payload).decode("utf-8")
            data = json.loads(decoded)
            return data.get("sub")
    except Exception as e:
        print(f"Error decoding user token: {e}")
        
    return None
