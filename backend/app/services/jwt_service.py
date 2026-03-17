import time
import jwt


class AuthError(Exception):
    pass


class JWTExpiredError(AuthError):
    pass


class JWTTenantMismatchError(AuthError):
    pass


class JWTMalformedError(AuthError):
    pass


def validate_jwt(token: str, tenant_id: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            options={"verify_signature": False},
            algorithms=["HS256", "RS256", "HS512", "RS512"],
        )
    except jwt.DecodeError as e:
        raise JWTMalformedError(f"Malformed JWT: {e}") from e

    exp = payload.get("exp")
    if exp is not None and exp < time.time():
        raise JWTExpiredError("JWT token has expired")

    tenant_claim = payload.get("tenant")
    if tenant_claim != tenant_id:
        raise JWTTenantMismatchError(
            f"JWT tenant claim does not match provided tenant_id"
        )

    return payload
