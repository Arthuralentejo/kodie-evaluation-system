from datetime import datetime

from bson import ObjectId
from pymongo import ReturnDocument


class AssessmentRepository:
    def __init__(self, collection, questions_collection):
        self.collection = collection
        self.questions_collection = questions_collection

    async def find_assessment_by_id(self, *, assessment_id: ObjectId) -> dict | None:
        return await self.collection.find_one({"_id": assessment_id})

    async def find_questions_by_ids(self, *, question_ids: list[ObjectId]) -> list[dict]:
        return await self.questions_collection.find({"_id": {"$in": question_ids}}).to_list(length=None)

    async def find_question_by_id(self, *, question_id: ObjectId) -> dict | None:
        return await self.questions_collection.find_one({"_id": question_id})

    async def find_draft_assessment_by_student(self, *, student_id: str) -> dict | None:
        return await self.collection.find_one(
            {"student_id": student_id, "status": "DRAFT", "archived": False}
        )

    async def find_active_assessment_by_student(self, *, student_id: str) -> dict | None:
        return await self.collection.find_one({"student_id": student_id, "archived": False})

    async def find_all_completed_assessments_by_student(self, *, student_id: str) -> list[dict]:
        # includes archived — full history
        return await self.collection.find(
            {"student_id": student_id, "status": "COMPLETED"},
            sort=[("completed_at", -1)],
        ).to_list(length=None)

    async def archive_assessment(self, *, assessment_id: ObjectId) -> None:
        await self.collection.update_one(
            {"_id": assessment_id},
            {"$set": {"archived": True}},
        )

    async def list_questions_for_level(self, *, level: str) -> list[dict]:
        return await self.questions_collection.find(
            {"category": level},
            {"_id": 1, "number": 1, "category": 1},
        ).to_list(length=None)

    async def create_assessment(
        self,
        *,
        student_id: str,
        assigned_question_ids: list[ObjectId],
        level: str,
        now: datetime,
    ) -> dict:
        document = {
            "student_id": student_id,
            "assigned_question_ids": assigned_question_ids,
            "answers": [],
            "status": "DRAFT",
            "level": level,
            "archived": False,
            "started_at": now,
            "completed_at": None,
        }
        result = await self.collection.insert_one(document)
        document["_id"] = result.inserted_id
        return document

    async def update_assessment_answers(self, *, assessment_id: ObjectId, answers: list[dict]) -> None:
        await self.collection.update_one(
            {"_id": assessment_id},
            {"$set": {"answers": answers}},
        )

    async def complete_assessment(self, *, assessment_id: ObjectId, completed_at: datetime) -> dict | None:
        return await self.collection.find_one_and_update(
            {"_id": assessment_id, "status": "DRAFT"},
            {"$set": {"status": "COMPLETED", "completed_at": completed_at}},
            return_document=ReturnDocument.AFTER,
        )
