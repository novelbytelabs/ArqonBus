"""Minimal JWT validation for ArqonBus WebSocket edge authentication.

Current implementation supports HS256 using only Python stdlib.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any, Dict, Iterable, Optional


class JWTAuthError(Exception):
    """Raised when JWT validation fails."""


def _b64url_decode(segment: str) -> bytes:
    padding = "=" * (-len(segment) % 4)
    try:
        return base64.urlsafe_b64decode((segment + padding).encode("ascii"))
    except Exception as exc:
        raise JWTAuthError("Invalid JWT encoding") from exc


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _decode_json_segment(segment: str) -> Dict[str, Any]:
    try:
        decoded = _b64url_decode(segment)
        value = json.loads(decoded.decode("utf-8"))
    except Exception as exc:
        raise JWTAuthError("Invalid JWT JSON payload") from exc
    if not isinstance(value, dict):
        raise JWTAuthError("JWT payload must be an object")
    return value


def _ensure_numeric_claim(payload: Dict[str, Any], claim_name: str) -> Optional[float]:
    if claim_name not in payload:
        return None
    value = payload[claim_name]
    if not isinstance(value, (int, float)):
        raise JWTAuthError(f"JWT claim '{claim_name}' must be numeric")
    return float(value)


def validate_jwt(
    token: str,
    secret: str,
    *,
    allowed_algorithms: Optional[Iterable[str]] = None,
    leeway_seconds: int = 0,
    now_ts: Optional[float] = None,
) -> Dict[str, Any]:
    """Validate a JWT and return claims.

    Args:
        token: JWT string.
        secret: Shared secret for HS256 signatures.
        allowed_algorithms: Allowed `alg` header values.
        leeway_seconds: Clock skew allowance for time claims.
        now_ts: Override current timestamp (test-only).
    """
    if not token or not isinstance(token, str):
        raise JWTAuthError("Missing JWT")
    if not secret:
        raise JWTAuthError("JWT secret is not configured")

    parts = token.split(".")
    if len(parts) != 3:
        raise JWTAuthError("Malformed JWT")

    header_b64, payload_b64, signature_b64 = parts
    header = _decode_json_segment(header_b64)
    payload = _decode_json_segment(payload_b64)

    allowed = set(allowed_algorithms or ("HS256",))
    alg = str(header.get("alg", "")).upper()
    if alg not in allowed:
        raise JWTAuthError("JWT algorithm is not allowed")
    if alg != "HS256":
        raise JWTAuthError("Only HS256 is supported")

    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    expected_sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    expected_b64 = _b64url_encode(expected_sig)
    if not hmac.compare_digest(expected_b64, signature_b64):
        raise JWTAuthError("Invalid JWT signature")

    now = float(now_ts if now_ts is not None else time.time())
    leeway = float(max(0, leeway_seconds))

    exp = _ensure_numeric_claim(payload, "exp")
    if exp is not None and now > (exp + leeway):
        raise JWTAuthError("JWT has expired")

    nbf = _ensure_numeric_claim(payload, "nbf")
    if nbf is not None and now + leeway < nbf:
        raise JWTAuthError("JWT is not yet valid")

    iat = _ensure_numeric_claim(payload, "iat")
    if iat is not None and iat > now + leeway:
        raise JWTAuthError("JWT issued-at is in the future")

    return payload


def issue_hs256_token(
    claims: Dict[str, Any],
    secret: str,
    *,
    header: Optional[Dict[str, Any]] = None,
) -> str:
    """Create an HS256 JWT (test helper)."""
    if not isinstance(claims, dict):
        raise JWTAuthError("Claims must be a dictionary")
    if not secret:
        raise JWTAuthError("JWT secret is required")

    token_header: Dict[str, Any] = {"typ": "JWT", "alg": "HS256"}
    if header:
        token_header.update(header)

    header_json = json.dumps(token_header, separators=(",", ":"), sort_keys=True).encode("utf-8")
    payload_json = json.dumps(claims, separators=(",", ":"), sort_keys=True).encode("utf-8")
    header_b64 = _b64url_encode(header_json)
    payload_b64 = _b64url_encode(payload_json)
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    signature_b64 = _b64url_encode(signature)
    return f"{header_b64}.{payload_b64}.{signature_b64}"
