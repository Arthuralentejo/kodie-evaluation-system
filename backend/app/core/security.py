import uuid
from datetime import UTC, datetime, timedelta

import jwt
from jwt import InvalidTokenError

from app.core.config import settings
from app.core.errors import AppError

REQUIRED_CLAIMS = {"sub", "iat", "exp", "jti"}


def create_access_token(*, student_id: str) -> tuple[str, dict[str, str | int]]:
    now = datetime.now(UTC)
    exp = now + timedelta(minutes=settings.jwt_ttl_minutes)
    claims = {
        "sub": student_id,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "jti": str(uuid.uuid4()),
    }
    token = jwt.encode(
        claims,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
        headers={"kid": settings.jwt_kid},
    )
    return token, claims


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
    except InvalidTokenError as exc:
        raise AppError(
            status_code=401, code="INVALID_TOKEN", message="Invalid or expired token"
        ) from exc

    missing = REQUIRED_CLAIMS.difference(payload.keys())
    if missing:
        raise AppError(
            status_code=401,
            code="INVALID_TOKEN_CLAIMS",
            message="Token is missing required claims",
            details={"missing": sorted(missing)},
        )

    return payload
