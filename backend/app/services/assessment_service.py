from datetime import UTC, datetime
import hashlib
import random

from bson import ObjectId

from app.core.config import settings
from app.core.errors import AppError
from app.repositories.assessment_repository import AssessmentRepository
from app.services.question_selection import build_assigned_question_ids


def _ensure_object_id(value: str, code: str = "INVALID_ID") -> ObjectId:
    if not ObjectId.is_valid(value):
        raise AppError(status_code=422, code=code, message="Invalid object ID")
    return ObjectId(value)


def deterministic_shuffle_options(*, assessment_id: str, question_id: str, options: list[dict]) -> list[dict]:
    seed = f"{assessment_id}:{question_id}:{settings.shuffle_seed_version}".encode("utf-8")
    seed_int = int(hashlib.sha256(seed).hexdigest(), 16)
    rnd = random.Random(seed_int)
    shuffled = [dict(item) for item in options]
    rnd.shuffle(shuffled)
    return shuffled


class AssessmentService:
    def __init__(self, repository: AssessmentRepository):
        self.repository = repository

    async def get_questions_for_assessment(self, *, assessment_id: str, quantity: int | None = None):
        assess_oid = _ensure_object_id(assessment_id)
        assessment = await self.repository.find_assessment_by_id(assessment_id=assess_oid)
        if not assessment:
            raise AppError(status_code=404, code="ASSESSMENT_NOT_FOUND", message="Assessment not found")

        assigned_question_ids = assessment.get("assigned_question_ids", [])
        question_docs = await self.repository.find_questions_by_ids(question_ids=assigned_question_ids)
        question_by_id = {question["_id"]: question for question in question_docs}
        ordered_questions = [question_by_id[question_id] for question_id in assigned_question_ids if question_id in question_by_id]
        if quantity is not None:
            ordered_questions = ordered_questions[:quantity]

        answer_by_question = {
            str(item["question_id"]): item["selected_option"]
            for item in assessment.get("answers", [])
        }

        response = []
        for q in ordered_questions:
            qid = str(q["_id"])
            response.append(
                {
                    "id": qid,
                    "statement": q["statement"],
                    "options": deterministic_shuffle_options(
                        assessment_id=assessment_id,
                        question_id=qid,
                        options=q["options"],
                    ),
                    "selected_option": answer_by_question.get(qid),
                }
            )

        return response

    async def upsert_answer(self, *, assessment_id: str, question_id: str, selected_option: str):
        assess_oid = _ensure_object_id(assessment_id)
        question_oid = _ensure_object_id(question_id, code="INVALID_QUESTION_ID")

        assessment = await self.repository.find_assessment_by_id(assessment_id=assess_oid)
        if not assessment:
            raise AppError(status_code=404, code="ASSESSMENT_NOT_FOUND", message="Assessment not found")
        if question_oid not in assessment.get("assigned_question_ids", []):
            raise AppError(status_code=404, code="QUESTION_NOT_FOUND", message="Question not assigned to assessment")

        question = await self.repository.find_question_by_id(question_id=question_oid)
        if not question:
            raise AppError(status_code=404, code="QUESTION_NOT_FOUND", message="Question not found")

        valid_keys = {option["key"] for option in question["options"]}
        if selected_option not in valid_keys and selected_option != "DONT_KNOW":
            raise AppError(
                status_code=422,
                code="INVALID_OPTION",
                message="Invalid selected option",
                details={"allowed": sorted(valid_keys | {"DONT_KNOW"})},
            )

        updated_answers: list[dict] = []
        updated = False
        answered_at = datetime.now(UTC)
        for answer in assessment.get("answers", []):
            if answer["question_id"] == question_oid:
                updated_answers.append(
                    {
                        "question_id": question_oid,
                        "selected_option": selected_option,
                        "answered_at": answered_at,
                    }
                )
                updated = True
            else:
                updated_answers.append(answer)

        if not updated:
            updated_answers.append(
                {
                    "question_id": question_oid,
                    "selected_option": selected_option,
                    "answered_at": answered_at,
                }
            )

        await self.repository.update_assessment_answers(assessment_id=assess_oid, answers=updated_answers)

    async def submit_assessment(self, *, assessment_id: str):
        assess_oid = _ensure_object_id(assessment_id)
        assessment = await self.repository.find_assessment_by_id(assessment_id=assess_oid)
        if not assessment:
            raise AppError(status_code=404, code="ASSESSMENT_NOT_FOUND", message="Assessment not found")

        if assessment["status"] == "COMPLETED":
            return {"status": "COMPLETED", "completed_at": assessment["completed_at"].isoformat()}

        question_ids = {str(item) for item in assessment.get("assigned_question_ids", [])}
        answered_ids = {str(item["question_id"]) for item in assessment.get("answers", [])}

        missing = sorted(question_ids - answered_ids)
        if missing:
            raise AppError(
                status_code=422,
                code="INCOMPLETE_ASSESSMENT",
                message="Assessment has unanswered questions",
                details={"missing_question_ids": missing},
            )

        now = datetime.now(UTC)
        result = await self.repository.complete_assessment(assessment_id=assess_oid, completed_at=now)

        if result is None:
            latest = await self.repository.find_assessment_by_id(assessment_id=assess_oid)
            if latest and latest["status"] == "COMPLETED":
                return {"status": "COMPLETED", "completed_at": latest["completed_at"].isoformat()}
            raise AppError(status_code=409, code="INVALID_STATE", message="Unable to complete assessment")

        return {"status": "COMPLETED", "completed_at": result["completed_at"].isoformat()}
