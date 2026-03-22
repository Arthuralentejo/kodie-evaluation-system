from datetime import date, datetime

import pytest
from bson import ObjectId

from app.services.auth_service import AuthService, _birth_date_query


class _AuthRepositoryStub:
    def __init__(self):
        self.student = None
        self.last_student_lookup = None
        self.questions = []
        self.doc = {"_id": ObjectId()}
        self.attempts = {}
        self.revoked = None

    async def find_attempt(self, *, kind, key):
        return self.attempts.get((kind, key))

    async def reset_attempt_window(self, *, attempt_id, now):
        return None

    async def create_attempt(self, *, kind, key, now):
        self.attempts[(kind, key)] = {
            "_id": ObjectId(),
            "kind": kind,
            "key": key,
            "count": 0,
            "window_start": now,
            "lock_until": None,
            "updated_at": now,
        }

    async def update_attempt(self, *, kind, key, update):
        attempt = self.attempts[(kind, key)]
        attempt["count"] = attempt.get("count", 0) + update.get("$inc", {}).get("count", 0)
        attempt.update(update.get("$set", {}))

    async def delete_attempt(self, *, kind, key):
        self.attempts.pop((kind, key), None)

    async def find_student_by_cpf_and_birth_date(self, *, cpf, birth_date_query):
        self.last_student_lookup = {"cpf": cpf, "birth_date": birth_date_query}
        return self.student

    async def list_questions_for_assignment(self):
        return self.questions

    async def get_or_create_draft_assessment(self, *, student_id, assigned_question_ids, now):
        self.doc.setdefault("student_id", student_id)
        self.doc.setdefault("assigned_question_ids", assigned_question_ids)
        self.doc.setdefault("answers", [])
        self.doc.setdefault("status", "DRAFT")
        self.doc.setdefault("started_at", now)
        return self.doc

    async def find_draft_assessment_by_student(self, *, student_id):
        return self.doc

    async def find_revoked_token(self, *, jti):
        return self.revoked

    async def revoke_token(self, *, jti, expires_at, revoked_at):
        self.revoked = {"jti": jti, "expires_at": expires_at, "revoked_at": revoked_at}

    async def find_assessment_by_id(self, *, assessment_id):
        return self.doc


class _Logger:
    def info(self, *args, **kwargs):
        return None


@pytest.mark.asyncio
async def test_auth_looks_up_student_by_birth_date_day_range(monkeypatch):
    repository = _AuthRepositoryStub()
    repository.student = {"_id": ObjectId()}
    repository.questions = [
        {"_id": ObjectId(), "number": 1, "category": "iniciante"},
        {"_id": ObjectId(), "number": 2, "category": "junior"},
    ]

    service = AuthService(repository=repository)
    monkeypatch.setattr(
        "app.services.auth_service.create_access_token",
        lambda **kwargs: ("token", {"assessment_id": str(repository.doc["_id"])}),
    )

    result = await service.authenticate_and_issue_token(
        cpf="52998224725",
        birth_date=date(2000, 1, 1),
        ip="127.0.0.1",
        request_id="req-1",
    )

    assert result["token"] == "token"
    assert repository.last_student_lookup["cpf"] == "52998224725"
    assert repository.last_student_lookup["birth_date"]["$gte"] == datetime(2000, 1, 1, 0, 0)
    assert repository.last_student_lookup["birth_date"]["$lt"] == datetime(2000, 1, 2, 0, 0)


def test_birth_date_query_covers_single_day():
    query = _birth_date_query(date(2000, 1, 1))

    assert query["$gte"] == datetime(2000, 1, 1, 0, 0)
    assert query["$lt"] == datetime(2000, 1, 2, 0, 0)
