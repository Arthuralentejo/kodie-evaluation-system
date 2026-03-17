from datetime import UTC, datetime
import hashlib
import random

from bson import ObjectId
from pymongo import ReturnDocument

from app.core.config import settings
from app.core.errors import AppError
from app.db.collections import answers_collection, assessments_collection, questions_collection


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
    def __init__(self, db):
        self.db = db

    async def get_questions_for_assessment(self, *, assessment_id: str, quantity: int | None = None):
        assess_oid = _ensure_object_id(assessment_id)
        assessment = await assessments_collection(self.db).find_one({"_id": assess_oid})
        if not assessment:
            raise AppError(status_code=404, code="ASSESSMENT_NOT_FOUND", message="Assessment not found")

        question_docs = await questions_collection(self.db).find({}).to_list(length=None)
        question_docs = sorted(question_docs, key=lambda item: item.get("number", 0))
        if quantity is not None:
            question_docs = question_docs[:quantity]

        answer_docs = await answers_collection(self.db).find({"assessment_id": assess_oid}).to_list(length=None)
        answer_by_question = {str(item["question_id"]): item["selected_option"] for item in answer_docs}

        response = []
        for q in question_docs:
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

        question = await questions_collection(self.db).find_one({"_id": question_oid})
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

        await answers_collection(self.db).update_one(
            {"assessment_id": assess_oid, "question_id": question_oid},
            {
                "$set": {
                    "selected_option": selected_option,
                    "answered_at": datetime.now(UTC),
                },
                "$setOnInsert": {
                    "assessment_id": assess_oid,
                    "question_id": question_oid,
                },
            },
            upsert=True,
        )

    async def submit_assessment(self, *, assessment_id: str):
        assess_oid = _ensure_object_id(assessment_id)
        assessment = await assessments_collection(self.db).find_one({"_id": assess_oid})
        if not assessment:
            raise AppError(status_code=404, code="ASSESSMENT_NOT_FOUND", message="Assessment not found")

        if assessment["status"] == "COMPLETED":
            return {"status": "COMPLETED", "completed_at": assessment["completed_at"].isoformat()}

        questions = await questions_collection(self.db).find({}, {"_id": 1}).to_list(length=None)
        question_ids = {str(item["_id"]) for item in questions}

        answers = await answers_collection(self.db).find({"assessment_id": assess_oid}, {"question_id": 1}).to_list(length=None)
        answered_ids = {str(item["question_id"]) for item in answers}

        missing = sorted(question_ids - answered_ids)
        if missing:
            raise AppError(
                status_code=422,
                code="INCOMPLETE_ASSESSMENT",
                message="Assessment has unanswered questions",
                details={"missing_question_ids": missing},
            )

        now = datetime.now(UTC)
        result = await assessments_collection(self.db).find_one_and_update(
            {"_id": assess_oid, "status": "DRAFT"},
            {"$set": {"status": "COMPLETED", "completed_at": now}},
            return_document=ReturnDocument.AFTER,
        )

        if result is None:
            latest = await assessments_collection(self.db).find_one({"_id": assess_oid})
            if latest and latest["status"] == "COMPLETED":
                return {"status": "COMPLETED", "completed_at": latest["completed_at"].isoformat()}
            raise AppError(status_code=409, code="INVALID_STATE", message="Unable to complete assessment")

        return {"status": "COMPLETED", "completed_at": result["completed_at"].isoformat()}
