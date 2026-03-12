from datetime import UTC, datetime

import pytest
from bson import ObjectId

from app.core.errors import AppError
from app.services import assessment_service


class _Cursor:
    def __init__(self, docs):
        self._docs = docs

    async def to_list(self, length=None):
        return self._docs


class _SimpleCollection:
    def __init__(self, *, find_one_map=None, find_docs=None):
        self.find_one_map = find_one_map or {}
        self.find_docs = find_docs or []

    async def find_one(self, query):
        for key, value in self.find_one_map.items():
            field, expected = key
            if query.get(field) == expected:
                return value
        return None

    def find(self, *args, **kwargs):
        return _Cursor(self.find_docs)


class _SubmitAssessments:
    def __init__(self, assessment_id: ObjectId, student_id: ObjectId):
        self.assessment_id = assessment_id
        self.student_id = student_id
        self.status = "DRAFT"
        self.completed_at = None
        self.transitions = 0

    async def find_one(self, query):
        if query.get("_id") != self.assessment_id:
            return None
        return {
            "_id": self.assessment_id,
            "student_id": self.student_id,
            "status": self.status,
            "completed_at": self.completed_at,
        }

    async def find_one_and_update(self, query, update, return_document=None):
        if query.get("_id") != self.assessment_id or query.get("status") != "DRAFT":
            return None
        if self.status != "DRAFT":
            return None
        self.status = "COMPLETED"
        self.completed_at = update["$set"]["completed_at"]
        self.transitions += 1
        return {
            "_id": self.assessment_id,
            "student_id": self.student_id,
            "status": self.status,
            "completed_at": self.completed_at,
        }


@pytest.mark.asyncio
async def test_get_questions_restores_saved_answers(monkeypatch):
    assessment_id = ObjectId()
    question_id = ObjectId()
    student_id = ObjectId()

    assessments = _SimpleCollection(find_one_map={("_id", assessment_id): {"_id": assessment_id, "student_id": student_id}})
    questions = _SimpleCollection(
        find_docs=[
            {
                "_id": question_id,
                "statement": "Q1",
                "options": [{"key": "A", "text": "x"}, {"key": "B", "text": "y"}],
            }
        ]
    )
    answers = _SimpleCollection(find_docs=[{"question_id": question_id, "selected_option": "B"}])

    monkeypatch.setattr(assessment_service, "assessments_collection", lambda _: assessments)
    monkeypatch.setattr(assessment_service, "questions_collection", lambda _: questions)
    monkeypatch.setattr(assessment_service, "answers_collection", lambda _: answers)

    result = await assessment_service.get_questions_for_assessment(assessment_id=str(assessment_id), db=object())
    assert result[0]["selected_option"] == "B"


@pytest.mark.asyncio
async def test_submit_incomplete_returns_missing_question_ids(monkeypatch):
    assessment_id = ObjectId()
    student_id = ObjectId()
    q1 = ObjectId()
    q2 = ObjectId()

    assessments = _SimpleCollection(
        find_one_map={
            ("_id", assessment_id): {"_id": assessment_id, "student_id": student_id, "status": "DRAFT"}
        }
    )
    questions = _SimpleCollection(find_docs=[{"_id": q1}, {"_id": q2}])
    answers = _SimpleCollection(find_docs=[{"question_id": q1}])

    monkeypatch.setattr(assessment_service, "assessments_collection", lambda _: assessments)
    monkeypatch.setattr(assessment_service, "questions_collection", lambda _: questions)
    monkeypatch.setattr(assessment_service, "answers_collection", lambda _: answers)

    with pytest.raises(AppError) as exc:
        await assessment_service.submit_assessment(assessment_id=str(assessment_id), db=object())

    assert exc.value.status_code == 422
    assert exc.value.details["missing_question_ids"] == [str(q2)]


@pytest.mark.asyncio
async def test_submit_is_idempotent_and_atomic(monkeypatch):
    assessment_id = ObjectId()
    student_id = ObjectId()
    q1 = ObjectId()

    assessments = _SubmitAssessments(assessment_id, student_id)
    questions = _SimpleCollection(find_docs=[{"_id": q1}])
    answers = _SimpleCollection(find_docs=[{"question_id": q1}])

    monkeypatch.setattr(assessment_service, "assessments_collection", lambda _: assessments)
    monkeypatch.setattr(assessment_service, "questions_collection", lambda _: questions)
    monkeypatch.setattr(assessment_service, "answers_collection", lambda _: answers)

    first = await assessment_service.submit_assessment(assessment_id=str(assessment_id), db=object())
    second = await assessment_service.submit_assessment(assessment_id=str(assessment_id), db=object())

    assert first["status"] == "COMPLETED"
    assert second["status"] == "COMPLETED"
    assert first["completed_at"] == second["completed_at"]
    assert assessments.transitions == 1
