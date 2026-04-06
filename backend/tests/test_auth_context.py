import pytest
from fastapi.security import HTTPAuthorizationCredentials
from starlette.requests import Request

from app.api import deps
from app.core.errors import AppError


def _request_with_assessment(assessment_id: str) -> Request:
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/assessments/x/questions",
        "raw_path": b"/assessments/x/questions",
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "server": ("test", 80),
        "path_params": {"assessment_id": assessment_id},
    }
    return Request(scope)


class _AuthServiceStub:
    def __init__(self, *, side_effect=None, payload=None):
        self.side_effect = side_effect
        self.payload = payload

    async def validate_access(self, *, token: str, assessment_id: str | None = None):
        if self.side_effect:
            raise self.side_effect
        return self.payload


@pytest.mark.asyncio
async def test_auth_context_denies_foreign_assessment():
    assessment_id = "507f1f77bcf86cd799439011"
    request = _request_with_assessment(assessment_id)

    auth_service = _AuthServiceStub(
        side_effect=AppError(
            status_code=403, code="FORBIDDEN", message="Assessment access denied"
        )
    )

    with pytest.raises(AppError) as exc:
        await deps.get_auth_context(
            request=request,
            credentials=HTTPAuthorizationCredentials(
                scheme="Bearer", credentials="token"
            ),
            auth_service=auth_service,
        )

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_auth_context_revocation_store_outage_returns_503():
    assessment_id = "507f1f77bcf86cd799439011"
    request = _request_with_assessment(assessment_id)

    auth_service = _AuthServiceStub(
        side_effect=AppError(
            status_code=503,
            code="REVOCATION_STORE_UNAVAILABLE",
            message="Revocation store unavailable",
        )
    )

    with pytest.raises(AppError) as exc:
        await deps.get_auth_context(
            request=request,
            credentials=HTTPAuthorizationCredentials(
                scheme="Bearer", credentials="token"
            ),
            auth_service=auth_service,
        )

    assert exc.value.status_code == 503
    assert exc.value.code == "REVOCATION_STORE_UNAVAILABLE"


@pytest.mark.asyncio
async def test_auth_context_rejects_revoked_token():
    assessment_id = "507f1f77bcf86cd799439011"
    request = _request_with_assessment(assessment_id)

    auth_service = _AuthServiceStub(
        side_effect=AppError(
            status_code=401, code="TOKEN_REVOKED", message="Token has been revoked"
        )
    )

    with pytest.raises(AppError) as exc:
        await deps.get_auth_context(
            request=request,
            credentials=HTTPAuthorizationCredentials(
                scheme="Bearer", credentials="token"
            ),
            auth_service=auth_service,
        )

    assert exc.value.status_code == 401
    assert exc.value.code == "TOKEN_REVOKED"
