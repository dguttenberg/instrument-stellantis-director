"""Shared-password gate (HTTP Basic) for the hosted app.

If APP_PASSWORD is set in the environment, every request must carry HTTP Basic
credentials whose password matches (the username is ignored — it's a single shared
password). If APP_PASSWORD is unset, the gate is off (local dev). /health stays open
so the host's health check works.
"""

from __future__ import annotations

import base64
import binascii
import hmac
import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

OPEN_PATHS = {"/health"}


def _password_ok(authorization: str, password: str) -> bool:
    if not authorization.lower().startswith("basic "):
        return False
    try:
        decoded = base64.b64decode(authorization.split(" ", 1)[1]).decode("utf-8")
    except (ValueError, binascii.Error, UnicodeDecodeError):
        return False
    _, _, supplied = decoded.partition(":")
    return hmac.compare_digest(supplied, password)


class PasswordGateMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        password = os.environ.get("APP_PASSWORD", "")
        if not password or request.url.path in OPEN_PATHS:
            return await call_next(request)
        if _password_ok(request.headers.get("authorization", ""), password):
            return await call_next(request)
        return Response(
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="Director (shared password)"'},
        )
