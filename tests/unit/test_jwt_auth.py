import time

import pytest

from arqonbus.security.jwt_auth import JWTAuthError, issue_hs256_token, validate_jwt


def test_validate_jwt_accepts_valid_hs256_token():
    now = int(time.time())
    token = issue_hs256_token(
        {"sub": "user-1", "role": "user", "tenant_id": "tenant-a", "exp": now + 60},
        "test-secret",
    )
    claims = validate_jwt(token, "test-secret")
    assert claims["sub"] == "user-1"
    assert claims["role"] == "user"
    assert claims["tenant_id"] == "tenant-a"


def test_validate_jwt_rejects_bad_signature():
    now = int(time.time())
    token = issue_hs256_token({"sub": "user-1", "exp": now + 60}, "secret-a")
    with pytest.raises(JWTAuthError):
        validate_jwt(token, "secret-b")


def test_validate_jwt_rejects_expired_token():
    now = int(time.time())
    token = issue_hs256_token({"sub": "user-1", "exp": now - 1}, "test-secret")
    with pytest.raises(JWTAuthError):
        validate_jwt(token, "test-secret")


def test_validate_jwt_rejects_unsupported_algorithm():
    now = int(time.time())
    token = issue_hs256_token({"sub": "user-1", "exp": now + 60}, "test-secret", header={"alg": "RS256"})
    with pytest.raises(JWTAuthError):
        validate_jwt(token, "test-secret")
