from datetime import UTC, date, datetime

import pytest
from bson import ObjectId

from app.services import auth_service


class _StudentsCollection:
    def __init__(self, student):
        self.student = student
        self.last_query = None

    async def find_one(self, query):
        self.last_query = query
        return self.student


class _AssessmentsCollection:
    def __init__(self):
        self.doc = {"_id": ObjectId()}

    async def find_one_and_update(self, *args, **kwargs):
        return self.doc


class _AttemptsCollection:
    async def find_one(self, query):
        return None

    async def delete_one(self, query):
        return None


class _Logger:
    def info(self, *args, **kwargs):
        return None


@pytest.mark.asyncio
async def test_auth_looks_up_student_by_birth_date_day_range(monkeypatch):
    student = {"_id": ObjectId()}
    students = _StudentsCollection(student)
    assessments = _AssessmentsCollection()
    attempts = _AttemptsCollection()

    monkeypatch.setattr(auth_service, "students_collection", lambda _: students)
    monkeypatch.setattr(auth_service, "assessments_collection", lambda _: assessments)
    monkeypatch.setattr(auth_service, "auth_attempts_collection", lambda _: attempts)
    monkeypatch.setattr(
        auth_service,
        "create_access_token",
        lambda **kwargs: ("token", {"assessment_id": str(assessments.doc["_id"])}),
    )

    result = await auth_service.authenticate_and_issue_token(
        cpf="52998224725",
        birth_date=date(2000, 1, 1),
        ip="127.0.0.1",
        db=object(),
        logger=_Logger(),
        request_id="req-1",
    )

    assert result["token"] == "token"
    assert students.last_query["cpf"] == "52998224725"
    assert students.last_query["birth_date"]["$gte"] == datetime(2000, 1, 1, 0, 0)
    assert students.last_query["birth_date"]["$lt"] == datetime(2000, 1, 2, 0, 0)


def test_birth_date_query_covers_single_day():
    query = auth_service._birth_date_query(date(2000, 1, 1))

    assert query["$gte"] == datetime(2000, 1, 1, 0, 0)
    assert query["$lt"] == datetime(2000, 1, 2, 0, 0)
