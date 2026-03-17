from datetime import UTC, date, datetime, time, timedelta
from typing import Any
import logging
from bson import ObjectId
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError, PyMongoError

from app.core.config import settings
from app.core.errors import AppError
from app.core.security import create_access_token, decode_access_token
from app.core.utils import mask_cpf
from app.db.collections import (
    assessments_collection,
    auth_attempts_collection,
    denylist_collection,
    students_collection,
)
logger = logging.getLogger("kodie.auth")

def _attempt_window_start(now: datetime) -> datetime:
    return now - timedelta(minutes=settings.rate_limit_window_minutes)


def _seconds_until(target: datetime, now: datetime) -> int:
    return max(1, int((target - now).total_seconds()))


def _birth_date_query(birth_date: date) -> dict[str, dict[str, datetime]]:
    start = datetime.combine(birth_date, time.min)
    end = start + timedelta(days=1)
    return {"$gte": start, "$lt": end}


class AuthService:
    def __init__(self, db):
        self.db = db

    async def _get_attempt_doc(self, kind: str, key: str, *, now: datetime) -> dict[str, Any] | None:
        doc = await auth_attempts_collection(self.db).find_one({"kind": kind, "key": key})
        if not doc:
            return None

        if doc.get("window_start") and doc["window_start"] < _attempt_window_start(now):
            await auth_attempts_collection(self.db).update_one(
                {"_id": doc["_id"]},
                {"$set": {"count": 0, "window_start": now}},
            )
            doc["count"] = 0
            doc["window_start"] = now
        return doc

    async def _increment_attempt(self, kind: str, key: str, *, now: datetime) -> dict[str, Any]:
        doc = await self._get_attempt_doc(kind, key, now=now)
        if not doc:
            doc = {
                "kind": kind,
                "key": key,
                "count": 0,
                "window_start": now,
                "lock_until": None,
                "updated_at": now,
            }
            await auth_attempts_collection(self.db).insert_one(doc)

        update = {
            "$inc": {"count": 1},
            "$set": {"updated_at": now},
        }
        if kind == "cpf" and doc.get("count", 0) + 1 >= settings.cpf_attempt_limit:
            lock_until = now + timedelta(minutes=settings.cpf_lock_minutes)
            update["$set"]["lock_until"] = lock_until

        await auth_attempts_collection(self.db).update_one({"kind": kind, "key": key}, update)
        return await auth_attempts_collection(self.db).find_one({"kind": kind, "key": key})

    async def _reset_attempts(self, kind: str, key: str) -> None:
        await auth_attempts_collection(self.db).delete_one({"kind": kind, "key": key})

    async def check_rate_limit(self, *, cpf: str, ip: str) -> None:
        now = datetime.now(UTC)
        cpf_doc = await self._get_attempt_doc("cpf", cpf, now=now)
        ip_doc = await self._get_attempt_doc("ip", ip, now=now)

        retry_candidates: list[int] = []

        if cpf_doc:
            lock_until = cpf_doc.get("lock_until")
            if lock_until and lock_until > now:
                retry_candidates.append(_seconds_until(lock_until, now))
            elif cpf_doc.get("count", 0) >= settings.cpf_attempt_limit:
                window_end = cpf_doc["window_start"] + timedelta(minutes=settings.rate_limit_window_minutes)
                retry_candidates.append(_seconds_until(window_end, now))

        if ip_doc and ip_doc.get("count", 0) >= settings.ip_attempt_limit:
            window_end = ip_doc["window_start"] + timedelta(minutes=settings.rate_limit_window_minutes)
            retry_candidates.append(_seconds_until(window_end, now))

        if retry_candidates:
            raise AppError(
                status_code=429,
                code="AUTH_RATE_LIMITED",
                message="Too many authentication attempts",
                details={"retry_after": max(retry_candidates)},
            )

    async def _get_or_create_draft_assessment(self, *, student_id: ObjectId) -> dict:
        now = datetime.now(UTC)
        try:
            doc = await assessments_collection(self.db).find_one_and_update(
                {"student_id": student_id, "status": "DRAFT"},
                {
                    "$setOnInsert": {
                        "student_id": student_id,
                        "status": "DRAFT",
                        "started_at": now,
                        "completed_at": None,
                    }
                },
                upsert=True,
                return_document=ReturnDocument.AFTER,
            )
            if doc:
                return doc
        except DuplicateKeyError:
            pass

        existing = await assessments_collection(self.db).find_one({"student_id": student_id, "status": "DRAFT"})
        if not existing:
            raise AppError(status_code=503, code="DRAFT_BOOTSTRAP_FAILED", message="Failed to bootstrap assessment")
        return existing

    async def authenticate_and_issue_token(self, *, cpf: str, birth_date: date, ip: str, request_id: str):
        await self.check_rate_limit(cpf=cpf, ip=ip)

        student = await students_collection(self.db).find_one({"cpf": cpf, "birth_date": _birth_date_query(birth_date)})
        if not student:
            await self._increment_attempt("cpf", cpf, now=datetime.now(UTC))
            await self._increment_attempt("ip", ip, now=datetime.now(UTC))
            logger.info(
                "auth_failed",
                extra={"request_id": request_id, "cpf": mask_cpf(cpf), "ip": ip, "reason": "invalid_credentials"},
            )
            raise AppError(status_code=401, code="INVALID_CREDENTIALS", message="CPF or birth date is invalid")

        await self._reset_attempts("cpf", cpf)
        await self._reset_attempts("ip", ip)

        draft = await self._get_or_create_draft_assessment(student_id=student["_id"])
        token, claims = create_access_token(student_id=str(student["_id"]), assessment_id=str(draft["_id"]))

        return {"token": token, "assessment_id": str(draft["_id"]), "claims": claims}

    async def revoke_token(self, *, jti: str, exp: int) -> None:
        expires_at = datetime.fromtimestamp(exp, tz=UTC)
        await denylist_collection(self.db).update_one(
            {"jti": jti},
            {"$set": {"jti": jti, "expires_at": expires_at, "revoked_at": datetime.now(UTC)}},
            upsert=True,
        )

    async def validate_access(self, *, token: str, assessment_id: str | None = None) -> dict[str, Any]:
        payload = decode_access_token(token)

        try:
            revoked = await denylist_collection(self.db).find_one({"jti": payload["jti"]})
        except PyMongoError as exc:
            raise AppError(status_code=503, code="REVOCATION_STORE_UNAVAILABLE", message="Revocation store unavailable") from exc

        if revoked:
            raise AppError(status_code=401, code="TOKEN_REVOKED", message="Token has been revoked")

        if assessment_id and assessment_id != payload["assessment_id"]:
            raise AppError(status_code=403, code="FORBIDDEN", message="Assessment access denied")

        if assessment_id:
            if not ObjectId.is_valid(assessment_id):
                raise AppError(status_code=422, code="INVALID_ID", message="Invalid object ID")
            record = await assessments_collection(self.db).find_one({"_id": ObjectId(assessment_id)})
            if not record:
                raise AppError(status_code=404, code="ASSESSMENT_NOT_FOUND", message="Assessment not found")
            if str(record["student_id"]) != payload["sub"]:
                raise AppError(status_code=403, code="FORBIDDEN", message="Assessment access denied")

        return payload
