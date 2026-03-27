from datetime import UTC, datetime
import hashlib
import logging
import random

from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from app.core.config import settings
from app.core.errors import AppError
from app.repositories.assessment_repository import AssessmentRepository
from app.services.question_selection import build_assigned_question_ids

logger = logging.getLogger("kodie.assessment")


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

    async def get_current_assessment(self, *, student_id: str):
        student_oid = _ensure_object_id(student_id, code="INVALID_STUDENT_ID")

        completed = await self.repository.find_latest_completed_assessment_by_student(student_id=student_oid)
        if completed:
            return {
                "status": "COMPLETED",
                "assessment_id": str(completed["_id"]),
                "completed_at": completed["completed_at"].isoformat() if completed.get("completed_at") else None,
            }

        draft = await self.repository.find_draft_assessment_by_student(student_id=student_oid)
        if draft:
            return {
                "status": "DRAFT",
                "assessment_id": str(draft["_id"]),
                "completed_at": None,
            }

        return {"status": "NONE", "assessment_id": None, "completed_at": None}

    async def create_assessment(self, *, student_id: str):
        student_oid = _ensure_object_id(student_id, code="INVALID_STUDENT_ID")

        completed = await self.repository.find_latest_completed_assessment_by_student(student_id=student_oid)
        if completed:
            raise AppError(
                status_code=409,
                code="ASSESSMENT_ALREADY_COMPLETED",
                message="Student already has a completed assessment",
            )

        existing_draft = await self.repository.find_draft_assessment_by_student(student_id=student_oid)
        if existing_draft:
            return {"assessment_id": str(existing_draft["_id"]), "status": "DRAFT"}

        question_docs = await self.repository.list_questions_for_assignment()
        assigned_question_ids = build_assigned_question_ids(question_docs)
        now = datetime.now(UTC)

        try:
            created = await self.repository.create_assessment(
                student_id=student_oid,
                assigned_question_ids=assigned_question_ids,
                now=now,
            )
        except DuplicateKeyError:
            existing_draft = await self.repository.find_draft_assessment_by_student(student_id=student_oid)
            if existing_draft:
                return {"assessment_id": str(existing_draft["_id"]), "status": "DRAFT"}
            raise AppError(status_code=503, code="DRAFT_BOOTSTRAP_FAILED", message="Failed to create assessment")

        return {"assessment_id": str(created["_id"]), "status": "DRAFT"}

    async def get_questions_for_assessment(
        self,
        *,
        assessment_id: str,
        quantity: int | None = None,
        request_id: str | None = None,
    ):
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

        logger.info(
            "assessment_questions_loaded request_id=%s assessment_id=%s stored_assigned_count=%s returned_count=%s quantity=%s answered_count=%s",
            request_id,
            assessment_id,
            len(assigned_question_ids),
            len(response),
            quantity,
            len(answer_by_question),
        )
        return response

    async def upsert_answer(
        self,
        *,
        assessment_id: str,
        question_id: str,
        selected_option: str,
        request_id: str | None = None,
    ):
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
        logger.info(
            "assessment_answer_saved request_id=%s assessment_id=%s question_id=%s selected_option=%s answer_count=%s",
            request_id,
            assessment_id,
            question_id,
            selected_option,
            len(updated_answers),
        )

    async def submit_assessment(self, *, assessment_id: str, request_id: str | None = None):
        assess_oid = _ensure_object_id(assessment_id)
        assessment = await self.repository.find_assessment_by_id(assessment_id=assess_oid)
        if not assessment:
            raise AppError(status_code=404, code="ASSESSMENT_NOT_FOUND", message="Assessment not found")

        if assessment["status"] == "COMPLETED":
            logger.info(
                "assessment_submit_idempotent request_id=%s assessment_id=%s completed_at=%s",
                request_id,
                assessment_id,
                assessment["completed_at"].isoformat(),
            )
            return {"status": "COMPLETED", "completed_at": assessment["completed_at"].isoformat()}

        required_question_ids = [
            str(item) for item in assessment.get("assigned_question_ids", [])[: settings.assessment_question_count]
        ]
        question_ids = set(required_question_ids)
        answered_ids = {str(item["question_id"]) for item in assessment.get("answers", [])}

        logger.info(
            "assessment_submit_attempt request_id=%s assessment_id=%s required_question_count=%s stored_assigned_count=%s answered_count=%s",
            request_id,
            assessment_id,
            len(required_question_ids),
            len(assessment.get("assigned_question_ids", [])),
            len(answered_ids),
        )

        missing = sorted(question_ids - answered_ids)
        if missing:
            logger.warning(
                "assessment_submit_incomplete request_id=%s assessment_id=%s missing_count=%s missing_question_ids=%s",
                request_id,
                assessment_id,
                len(missing),
                ",".join(missing),
            )
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
                logger.info(
                    "assessment_submit_raced_to_completed request_id=%s assessment_id=%s completed_at=%s",
                    request_id,
                    assessment_id,
                    latest["completed_at"].isoformat(),
                )
                return {"status": "COMPLETED", "completed_at": latest["completed_at"].isoformat()}
            raise AppError(status_code=409, code="INVALID_STATE", message="Unable to complete assessment")

        logger.info(
            "assessment_submit_completed request_id=%s assessment_id=%s completed_at=%s",
            request_id,
            assessment_id,
            result["completed_at"].isoformat(),
        )
        return {"status": "COMPLETED", "completed_at": result["completed_at"].isoformat()}
