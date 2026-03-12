from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from fastapi.security import HTTPAuthorizationCredentials
from pymongo.errors import PyMongoError
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


@pytest.mark.asyncio
async def test_auth_context_denies_foreign_assessment(monkeypatch):
    assessment_id = "507f1f77bcf86cd799439011"
    request = _request_with_assessment(assessment_id)

    payload = {
        "sub": "507f1f77bcf86cd799439012",
        "assessment_id": assessment_id,
        "jti": "j1",
        "exp": int((datetime.now(UTC) + timedelta(minutes=30)).timestamp()),
    }
    monkeypatch.setattr(deps, "decode_access_token", lambda _: payload)
    monkeypatch.setattr(deps, "get_db", lambda: object())

    denylist = type("Deny", (), {"find_one": AsyncMock(return_value=None)})()
    assessments = type(
        "Assessments",
        (),
        {"find_one": AsyncMock(return_value={"_id": object(), "student_id": "507f1f77bcf86cd799439013"})},
    )()

    monkeypatch.setattr(deps, "denylist_collection", lambda _: denylist)
    monkeypatch.setattr(deps, "assessments_collection", lambda _: assessments)

    with pytest.raises(AppError) as exc:
        await deps.get_auth_context(
            request=request,
            credentials=HTTPAuthorizationCredentials(scheme="Bearer", credentials="token"),
        )

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_auth_context_revocation_store_outage_returns_503(monkeypatch):
    assessment_id = "507f1f77bcf86cd799439011"
    request = _request_with_assessment(assessment_id)

    payload = {
        "sub": "507f1f77bcf86cd799439012",
        "assessment_id": assessment_id,
        "jti": "j1",
        "exp": int((datetime.now(UTC) + timedelta(minutes=30)).timestamp()),
    }
    monkeypatch.setattr(deps, "decode_access_token", lambda _: payload)
    monkeypatch.setattr(deps, "get_db", lambda: object())

    denylist = type("Deny", (), {"find_one": AsyncMock(side_effect=PyMongoError("down"))})()
    monkeypatch.setattr(deps, "denylist_collection", lambda _: denylist)

    with pytest.raises(AppError) as exc:
        await deps.get_auth_context(
            request=request,
            credentials=HTTPAuthorizationCredentials(scheme="Bearer", credentials="token"),
        )

    assert exc.value.status_code == 503
    assert exc.value.code == "REVOCATION_STORE_UNAVAILABLE"


@pytest.mark.asyncio
async def test_auth_context_rejects_revoked_token(monkeypatch):
    assessment_id = "507f1f77bcf86cd799439011"
    request = _request_with_assessment(assessment_id)

    payload = {
        "sub": "507f1f77bcf86cd799439012",
        "assessment_id": assessment_id,
        "jti": "revoked-jti",
        "exp": int((datetime.now(UTC) + timedelta(minutes=30)).timestamp()),
    }
    monkeypatch.setattr(deps, "decode_access_token", lambda _: payload)
    monkeypatch.setattr(deps, "get_db", lambda: object())

    denylist = type("Deny", (), {"find_one": AsyncMock(return_value={"jti": "revoked-jti"})})()
    monkeypatch.setattr(deps, "denylist_collection", lambda _: denylist)

    with pytest.raises(AppError) as exc:
        await deps.get_auth_context(
            request=request,
            credentials=HTTPAuthorizationCredentials(scheme="Bearer", credentials="token"),
        )

    assert exc.value.status_code == 401
    assert exc.value.code == "TOKEN_REVOKED"
