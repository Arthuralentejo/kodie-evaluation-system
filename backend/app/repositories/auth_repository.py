from datetime import datetime
from typing import Any

from bson import ObjectId
from pymongo import ReturnDocument

from app.db.collections import (
    assessments_collection,
    auth_attempts_collection,
    denylist_collection,
    questions_collection,
    students_collection,
)


class AuthRepository:
    def __init__(self, db):
        self.db = db

    async def find_attempt(self, *, kind: str, key: str) -> dict[str, Any] | None:
        return await auth_attempts_collection(self.db).find_one({"kind": kind, "key": key})

    async def reset_attempt_window(self, *, attempt_id: ObjectId, now: datetime) -> None:
        await auth_attempts_collection(self.db).update_one(
            {"_id": attempt_id},
            {"$set": {"count": 0, "window_start": now}},
        )

    async def create_attempt(self, *, kind: str, key: str, now: datetime) -> None:
        await auth_attempts_collection(self.db).insert_one(
            {
                "kind": kind,
                "key": key,
                "count": 0,
                "window_start": now,
                "lock_until": None,
                "updated_at": now,
            }
        )

    async def update_attempt(self, *, kind: str, key: str, update: dict[str, Any]) -> None:
        await auth_attempts_collection(self.db).update_one({"kind": kind, "key": key}, update)

    async def delete_attempt(self, *, kind: str, key: str) -> None:
        await auth_attempts_collection(self.db).delete_one({"kind": kind, "key": key})

    async def find_student_by_cpf_and_birth_date(self, *, cpf: str, birth_date_query: dict[str, Any]) -> dict | None:
        return await students_collection(self.db).find_one({"cpf": cpf, "birth_date": birth_date_query})

    async def list_questions_for_assignment(self) -> list[dict]:
        return await questions_collection(self.db).find({}, {"_id": 1, "number": 1, "category": 1}).to_list(length=None)

    async def get_or_create_draft_assessment(
        self,
        *,
        student_id: ObjectId,
        assigned_question_ids: list[ObjectId],
        now: datetime,
    ) -> dict | None:
        return await assessments_collection(self.db).find_one_and_update(
            {"student_id": student_id, "status": "DRAFT"},
            {
                "$setOnInsert": {
                    "student_id": student_id,
                    "assigned_question_ids": assigned_question_ids,
                    "answers": [],
                    "status": "DRAFT",
                    "started_at": now,
                    "completed_at": None,
                }
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )

    async def find_draft_assessment_by_student(self, *, student_id: ObjectId) -> dict | None:
        return await assessments_collection(self.db).find_one({"student_id": student_id, "status": "DRAFT"})

    async def find_revoked_token(self, *, jti: str) -> dict | None:
        return await denylist_collection(self.db).find_one({"jti": jti})

    async def revoke_token(self, *, jti: str, expires_at: datetime, revoked_at: datetime) -> None:
        await denylist_collection(self.db).update_one(
            {"jti": jti},
            {"$set": {"jti": jti, "expires_at": expires_at, "revoked_at": revoked_at}},
            upsert=True,
        )

    async def find_assessment_by_id(self, *, assessment_id: ObjectId) -> dict | None:
        return await assessments_collection(self.db).find_one({"_id": assessment_id})
