from datetime import datetime
from typing import Any

from bson import ObjectId

from app.core.logger import build_log_message, get_logger, hash_identifier
from app.core.utils import mask_cpf
from app.db.collections import (
    assessments_collection,
    auth_attempts_collection,
    denylist_collection,
    students_collection,
)

logger = get_logger("kodie.repositories.auth")


class AuthRepository:
    def __init__(self, db):
        self.db = db

    async def find_attempt(self, *, kind: str, key: str) -> dict[str, Any] | None:
        result = await auth_attempts_collection(self.db).find_one(
            {"kind": kind, "key": key}
        )
        logger.info(
            build_log_message(
                "auth_attempt_lookup_completed",
                kind=kind,
                key_ref=mask_cpf(key) if kind == "cpf" else hash_identifier(key),
                found=result is not None,
                count=result.get("count") if result else None,
                locked=result.get("lock_until") is not None if result else None,
            )
        )
        return result

    async def reset_attempt_window(
        self, *, attempt_id: ObjectId, now: datetime
    ) -> None:
        await auth_attempts_collection(self.db).update_one(
            {"_id": attempt_id},
            {"$set": {"count": 0, "window_start": now}},
        )
        logger.info(
            build_log_message(
                "auth_attempt_window_reset",
                attempt_id=str(attempt_id),
                window_start=now,
            )
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
        logger.info(
            build_log_message(
                "auth_attempt_created",
                kind=kind,
                key_ref=mask_cpf(key) if kind == "cpf" else hash_identifier(key),
                created_at=now,
            )
        )

    async def update_attempt(
        self, *, kind: str, key: str, update: dict[str, Any]
    ) -> None:
        await auth_attempts_collection(self.db).update_one(
            {"kind": kind, "key": key}, update
        )
        logger.info(
            build_log_message(
                "auth_attempt_updated",
                kind=kind,
                key_ref=mask_cpf(key) if kind == "cpf" else hash_identifier(key),
                updated_fields=sorted(update.keys()),
            )
        )

    async def delete_attempt(self, *, kind: str, key: str) -> None:
        await auth_attempts_collection(self.db).delete_one({"kind": kind, "key": key})
        logger.info(
            build_log_message(
                "auth_attempt_deleted",
                kind=kind,
                key_ref=mask_cpf(key) if kind == "cpf" else hash_identifier(key),
            )
        )

    async def find_student_by_cpf_and_birth_date(
        self, *, cpf: str, birth_date_query: dict[str, Any]
    ) -> dict | None:
        result = await students_collection(self.db).find_one(
            {"cpf": cpf, "birth_date": birth_date_query}
        )
        logger.info(
            build_log_message(
                "student_lookup_by_cpf_completed",
                cpf=mask_cpf(cpf),
                found=result is not None,
                student_ref=hash_identifier(result.get("student_id") or result["_id"])
                if result
                else None,
            )
        )
        return result

    async def find_revoked_token(self, *, jti: str) -> dict | None:
        result = await denylist_collection(self.db).find_one({"jti": jti})
        logger.info(
            build_log_message(
                "token_revocation_lookup_completed",
                jti_ref=hash_identifier(jti),
                found=result is not None,
            )
        )
        return result

    async def revoke_token(
        self, *, jti: str, expires_at: datetime, revoked_at: datetime
    ) -> None:
        await denylist_collection(self.db).update_one(
            {"jti": jti},
            {"$set": {"jti": jti, "expires_at": expires_at, "revoked_at": revoked_at}},
            upsert=True,
        )
        logger.info(
            build_log_message(
                "token_revocation_saved",
                jti_ref=hash_identifier(jti),
                expires_at=expires_at,
                revoked_at=revoked_at,
            )
        )

    async def find_assessment_by_id(self, *, assessment_id: ObjectId) -> dict | None:
        result = await assessments_collection(self.db).find_one({"_id": assessment_id})
        logger.info(
            build_log_message(
                "auth_assessment_lookup_completed",
                assessment_id=str(assessment_id),
                found=result is not None,
                status=result.get("status") if result else None,
            )
        )
        return result
