"""Logins: password hashing, signed tokens, and the staff-only check.

Two layers protect the API. The X-API-Key header says "this is our web page" (and is public in
that page). A login token says "this is a signed-in person with this role" and is what keeps
patients out of the dashboard. Only the standard library is used.

A token is `<payload>.<signature>`: the payload is base64url JSON {sub, role, exp} and the
signature is HMAC-SHA256 of the payload with AUTH_SECRET. Nothing is stored on the server.
"""

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Annotated, Literal

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import TOKEN_LIFETIME_SECONDS
from app.errors import ForbiddenError, UnauthorizedError

Role = Literal["staff", "patient"]

# scrypt cost: 16 MB of memory and roughly 50 ms per check. Fine for a small clinic.
_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SALT_BYTES = 16


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


# --- passwords ----------------------------------------------------------------------------------


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(_SALT_BYTES)
    digest = hashlib.scrypt(
        password.encode(), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P, dklen=32
    )
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    """True when the password matches the stored hash. Never raises on a malformed hash."""
    try:
        scheme, n, r, p, salt, expected = stored.split("$")
        if scheme != "scrypt":
            return False
        digest = hashlib.scrypt(
            password.encode(), salt=_unb64(salt), n=int(n), r=int(r), p=int(p), dklen=32
        )
        return hmac.compare_digest(digest, _unb64(expected))
    except (ValueError, TypeError):
        return False


# A real hash of a random password, checked when the email is unknown, so "no such user" and
# "wrong password" take about the same time.
DUMMY_HASH = hash_password(secrets.token_urlsafe(16))


# --- tokens -------------------------------------------------------------------------------------


def _sign(secret: str, payload: str) -> str:
    return _b64(hmac.new(secret.encode(), payload.encode(), hashlib.sha256).digest())


def issue_token(secret: str, user_id: str, role: str, now: float | None = None) -> tuple[str, int]:
    """A signed token for this user, and the unix time it expires."""
    expires = int((time.time() if now is None else now) + TOKEN_LIFETIME_SECONDS)
    payload = _b64(json.dumps({"sub": user_id, "role": role, "exp": expires}).encode())
    return f"{payload}.{_sign(secret, payload)}", expires


def read_token(secret: str, token: str, now: float | None = None) -> dict | None:
    """The token's claims, or None when it is forged, damaged or expired."""
    try:
        payload, signature = token.split(".")
        if not hmac.compare_digest(signature, _sign(secret, payload)):
            return None
        claims = json.loads(_unb64(payload))
        if not isinstance(claims, dict) or claims.get("role") not in ("staff", "patient"):
            return None
        if int(claims["exp"]) <= (time.time() if now is None else now):
            return None
        return claims
    except (ValueError, TypeError, KeyError):
        return None


# --- the check used by routes -------------------------------------------------------------------

# Also adds the "Authorize" bearer box to /docs. auto_error=False so our own 401 is used.
_bearer = HTTPBearer(auto_error=False)


def require_staff(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> dict:
    """Dependency: 401 without a valid login, 403 for a signed-in patient."""
    if credentials is None:
        raise UnauthorizedError("sign in to continue")
    claims = read_token(request.app.state.settings.auth_secret, credentials.credentials)
    if claims is None:
        raise UnauthorizedError("sign in to continue")
    if claims["role"] != "staff":
        raise ForbiddenError("staff only")
    return claims
