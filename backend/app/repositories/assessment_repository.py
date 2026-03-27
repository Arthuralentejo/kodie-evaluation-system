from datetime import datetime

from bson import ObjectId
from pymongo import ReturnDocument

from app.db.collections import assessments_collection, questions_collection


class AssessmentRepository:
    def __init__(self, db):
        self.db = db

    async def find_assessment_by_id(self, *, assessment_id: ObjectId) -> dict | None:
        return await assessments_collection(self.db).find_one({"_id": assessment_id})

    async def find_questions_by_ids(self, *, question_ids: list[ObjectId]) -> list[dict]:
        return await questions_collection(self.db).find({"_id": {"$in": question_ids}}).to_list(length=None)

    async def find_question_by_id(self, *, question_id: ObjectId) -> dict | None:
        return await questions_collection(self.db).find_one({"_id": question_id})

    async def list_questions_for_assignment(self) -> list[dict]:
        return await questions_collection(self.db).find({}, {"_id": 1, "number": 1, "category": 1}).to_list(length=None)

    async def find_draft_assessment_by_student(self, *, student_id: ObjectId) -> dict | None:
        return await assessments_collection(self.db).find_one({"student_id": student_id, "status": "DRAFT"})

    async def find_latest_completed_assessment_by_student(self, *, student_id: ObjectId) -> dict | None:
        return await assessments_collection(self.db).find_one(
            {"student_id": student_id, "status": "COMPLETED"},
            sort=[("completed_at", -1), ("_id", -1)],
        )

    async def create_assessment(
        self,
        *,
        student_id: ObjectId,
        assigned_question_ids: list[ObjectId],
        now: datetime,
    ) -> dict:
        document = {
            "student_id": student_id,
            "assigned_question_ids": assigned_question_ids,
            "answers": [],
            "status": "DRAFT",
            "started_at": now,
            "completed_at": None,
        }
        result = await assessments_collection(self.db).insert_one(document)
        document["_id"] = result.inserted_id
        return document

    async def update_assessment_answers(self, *, assessment_id: ObjectId, answers: list[dict]) -> None:
        await assessments_collection(self.db).update_one(
            {"_id": assessment_id},
            {"$set": {"answers": answers}},
        )

    async def complete_assessment(self, *, assessment_id: ObjectId, completed_at: datetime) -> dict | None:
        return await assessments_collection(self.db).find_one_and_update(
            {"_id": assessment_id, "status": "DRAFT"},
            {"$set": {"status": "COMPLETED", "completed_at": completed_at}},
            return_document=ReturnDocument.AFTER,
        )
