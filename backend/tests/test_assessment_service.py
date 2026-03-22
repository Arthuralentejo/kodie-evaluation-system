from datetime import UTC, datetime

import pytest
from bson import ObjectId

from app.core.errors import AppError
from app.services.assessment_service import AssessmentService


class _AssessmentRepositoryStub:
    def __init__(self):
        self.assessments = {}
        self.questions = {}
        self.last_update_answers = None
        self.complete_calls = 0

    async def find_assessment_by_id(self, *, assessment_id):
        return self.assessments.get(assessment_id)

    async def find_questions_by_ids(self, *, question_ids):
        return [self.questions[question_id] for question_id in question_ids if question_id in self.questions]

    async def find_question_by_id(self, *, question_id):
        return self.questions.get(question_id)

    async def update_assessment_answers(self, *, assessment_id, answers):
        self.last_update_answers = {"assessment_id": assessment_id, "answers": answers}
        assessment = self.assessments[assessment_id]
        assessment["answers"] = answers

    async def complete_assessment(self, *, assessment_id, completed_at):
        assessment = self.assessments.get(assessment_id)
        if not assessment or assessment["status"] != "DRAFT":
            return None
        assessment["status"] = "COMPLETED"
        assessment["completed_at"] = completed_at
        self.complete_calls += 1
        return assessment


@pytest.mark.asyncio
async def test_get_questions_restores_saved_answers(monkeypatch):
    assessment_id = ObjectId()
    question_id = ObjectId()
    student_id = ObjectId()
    repository = _AssessmentRepositoryStub()
    repository.assessments[assessment_id] = {
        "_id": assessment_id,
        "student_id": student_id,
        "assigned_question_ids": [question_id],
        "answers": [{"question_id": question_id, "selected_option": "B"}],
    }
    repository.questions[question_id] = {
        "_id": question_id,
        "statement": "Q1",
        "options": [{"key": "A", "text": "x"}, {"key": "B", "text": "y"}],
    }

    service = AssessmentService(repository=repository)

    result = await service.get_questions_for_assessment(assessment_id=str(assessment_id))
    assert result[0]["selected_option"] == "B"


@pytest.mark.asyncio
async def test_submit_incomplete_returns_missing_question_ids(monkeypatch):
    assessment_id = ObjectId()
    student_id = ObjectId()
    q1 = ObjectId()
    q2 = ObjectId()
    repository = _AssessmentRepositoryStub()
    repository.assessments[assessment_id] = {
        "_id": assessment_id,
        "student_id": student_id,
        "status": "DRAFT",
        "assigned_question_ids": [q1, q2],
        "answers": [{"question_id": q1, "selected_option": "A"}],
    }

    service = AssessmentService(repository=repository)

    with pytest.raises(AppError) as exc:
        await service.submit_assessment(assessment_id=str(assessment_id))

    assert exc.value.status_code == 422
    assert exc.value.details["missing_question_ids"] == [str(q2)]


@pytest.mark.asyncio
async def test_submit_is_idempotent_and_atomic(monkeypatch):
    assessment_id = ObjectId()
    student_id = ObjectId()
    q1 = ObjectId()
    repository = _AssessmentRepositoryStub()
    repository.assessments[assessment_id] = {
        "_id": assessment_id,
        "student_id": student_id,
        "assigned_question_ids": [q1],
        "answers": [{"question_id": q1, "selected_option": "A"}],
        "status": "DRAFT",
        "completed_at": None,
    }

    service = AssessmentService(repository=repository)

    first = await service.submit_assessment(assessment_id=str(assessment_id))
    second = await service.submit_assessment(assessment_id=str(assessment_id))

    assert first["status"] == "COMPLETED"
    assert second["status"] == "COMPLETED"
    assert first["completed_at"] == second["completed_at"]
    assert repository.complete_calls == 1


@pytest.mark.asyncio
async def test_get_questions_honors_quantity(monkeypatch):
    assessment_id = ObjectId()
    student_id = ObjectId()
    q1 = ObjectId()
    q2 = ObjectId()
    repository = _AssessmentRepositoryStub()
    repository.assessments[assessment_id] = {
        "_id": assessment_id,
        "student_id": student_id,
        "assigned_question_ids": [q1, q2],
        "answers": [],
    }
    repository.questions[q1] = {"_id": q1, "number": 1, "statement": "Q1", "options": [{"key": "A", "text": "x"}]}
    repository.questions[q2] = {"_id": q2, "number": 2, "statement": "Q2", "options": [{"key": "A", "text": "y"}]}

    service = AssessmentService(repository=repository)

    result = await service.get_questions_for_assessment(assessment_id=str(assessment_id), quantity=1)

    assert len(result) == 1
    assert result[0]["statement"] == "Q1"


@pytest.mark.asyncio
async def test_get_questions_distributes_difficulties_with_fewer_senior(monkeypatch):
    assessment_id = ObjectId()
    student_id = ObjectId()

    ordered_ids = [ObjectId() for _ in range(10)]
    repository = _AssessmentRepositoryStub()
    repository.assessments[assessment_id] = {
        "_id": assessment_id,
        "student_id": student_id,
        "assigned_question_ids": ordered_ids,
        "answers": [],
    }
    docs = [
        {"_id": ordered_ids[0], "number": 1, "category": "iniciante", "statement": "I1", "options": [{"key": "A", "text": "a"}]},
        {"_id": ordered_ids[1], "number": 2, "category": "iniciante", "statement": "I2", "options": [{"key": "A", "text": "a"}]},
        {"_id": ordered_ids[2], "number": 3, "category": "iniciante", "statement": "I3", "options": [{"key": "A", "text": "a"}]},
        {"_id": ordered_ids[3], "number": 4, "category": "iniciante", "statement": "I4", "options": [{"key": "A", "text": "a"}]},
        {"_id": ordered_ids[4], "number": 5, "category": "junior", "statement": "J1", "options": [{"key": "A", "text": "a"}]},
        {"_id": ordered_ids[5], "number": 6, "category": "junior", "statement": "J2", "options": [{"key": "A", "text": "a"}]},
        {"_id": ordered_ids[6], "number": 7, "category": "junior", "statement": "J3", "options": [{"key": "A", "text": "a"}]},
        {"_id": ordered_ids[7], "number": 8, "category": "pleno", "statement": "P1", "options": [{"key": "A", "text": "a"}]},
        {"_id": ordered_ids[8], "number": 9, "category": "pleno", "statement": "P2", "options": [{"key": "A", "text": "a"}]},
        {"_id": ordered_ids[9], "number": 10, "category": "senior", "statement": "S1", "options": [{"key": "A", "text": "a"}]},
    ]
    for doc in docs:
        repository.questions[doc["_id"]] = doc

    service = AssessmentService(repository=repository)

    result = await service.get_questions_for_assessment(assessment_id=str(assessment_id), quantity=10)

    statements = [item["statement"] for item in result]
    assert len(result) == 10
    assert sum(statement.startswith("I") for statement in statements) == 4
    assert sum(statement.startswith("J") for statement in statements) == 3
    assert sum(statement.startswith("P") for statement in statements) == 2
    assert sum(statement.startswith("S") for statement in statements) == 1


@pytest.mark.asyncio
async def test_upsert_answer_updates_embedded_answers(monkeypatch):
    assessment_id = ObjectId()
    question_id = ObjectId()
    student_id = ObjectId()
    repository = _AssessmentRepositoryStub()
    repository.assessments[assessment_id] = {
        "_id": assessment_id,
        "student_id": student_id,
        "assigned_question_ids": [question_id],
        "answers": [],
        "status": "DRAFT",
    }
    repository.questions[question_id] = {"_id": question_id, "options": [{"key": "A", "text": "a"}]}

    service = AssessmentService(repository=repository)

    await service.upsert_answer(assessment_id=str(assessment_id), question_id=str(question_id), selected_option="A")

    payload = repository.last_update_answers["answers"]
    assert len(payload) == 1
    assert payload[0]["question_id"] == question_id
    assert payload[0]["selected_option"] == "A"
