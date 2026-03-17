import time
import jwt
import pytest

from app.services.jwt_service import (
    validate_jwt,
    JWTExpiredError,
    JWTTenantMismatchError,
    JWTMalformedError,
)


def _make_token(payload: dict) -> str:
    return jwt.encode(payload, "secret", algorithm="HS256")


def test_valid_jwt_matching_tenant():
    payload = {"tenant": "acme-corp", "exp": int(time.time()) + 3600}
    token = _make_token(payload)
    result = validate_jwt(token, "acme-corp")
    assert result["tenant"] == "acme-corp"


def test_expired_jwt():
    payload = {"tenant": "acme-corp", "exp": int(time.time()) - 100}
    token = _make_token(payload)
    with pytest.raises(JWTExpiredError):
        validate_jwt(token, "acme-corp")


def test_tenant_mismatch():
    payload = {"tenant": "other-tenant", "exp": int(time.time()) + 3600}
    token = _make_token(payload)
    with pytest.raises(JWTTenantMismatchError):
        validate_jwt(token, "acme-corp")


def test_malformed_jwt():
    with pytest.raises(JWTMalformedError):
        validate_jwt("this-is-not-a-jwt", "acme-corp")
