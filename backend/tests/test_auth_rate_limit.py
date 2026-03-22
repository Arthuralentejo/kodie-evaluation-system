from datetime import UTC, datetime, timedelta

import pytest

from app.core.errors import AppError
from app.services.auth_service import AuthService


class _Logger:
    def info(self, *args, **kwargs):
        return None


class _AuthRepositoryStub:
    def __init__(self):
        self.attempts = {}

    async def find_attempt(self, *, kind, key):
        return self.attempts.get((kind, key))


@pytest.mark.asyncio
async def test_check_rate_limit_uses_retry_after(monkeypatch):
    now = datetime.now(UTC)
    service = AuthService(repository=_AuthRepositoryStub())

    async def fake_get_attempt_doc(kind, key, *, now):
        if kind == "cpf":
            return {
                "kind": "cpf",
                "key": key,
                "count": 5,
                "window_start": now - timedelta(minutes=1),
                "lock_until": now + timedelta(minutes=5),
            }
        return None

    monkeypatch.setattr(service, "_get_attempt_doc", fake_get_attempt_doc)

    with pytest.raises(AppError) as exc:
        await service.check_rate_limit(cpf="52998224725", ip="127.0.0.1")

    assert exc.value.status_code == 429
    assert exc.value.details["retry_after"] > 0


@pytest.mark.asyncio
async def test_check_rate_limit_blocks_by_ip_threshold(monkeypatch):
    now = datetime.now(UTC)
    service = AuthService(repository=_AuthRepositoryStub())

    async def fake_get_attempt_doc(kind, key, *, now):
        if kind == "ip":
            return {
                "kind": "ip",
                "key": key,
                "count": 20,
                "window_start": now - timedelta(minutes=2),
                "lock_until": None,
            }
        return None

    monkeypatch.setattr(service, "_get_attempt_doc", fake_get_attempt_doc)

    with pytest.raises(AppError) as exc:
        await service.check_rate_limit(cpf="52998224725", ip="10.0.0.1")

    assert exc.value.status_code == 429
    assert exc.value.details["retry_after"] > 0
