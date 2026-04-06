from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from bson import ObjectId
from pymongo.errors import PyMongoError

from app.core.config import settings
from app.core.errors import AppError
from app.core.logger import build_log_message, get_logger, hash_identifier
from app.core.security import create_access_token, decode_access_token
from app.core.utils import mask_cpf
from app.repositories.auth_repository import AuthRepository

logger = get_logger("kodie.auth")


def _coerce_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _attempt_window_start(now: datetime) -> datetime:
    return now - timedelta(minutes=settings.rate_limit_window_minutes)


def _seconds_until(target: datetime, now: datetime) -> int:
    return max(1, int((target - now).total_seconds()))


def _birth_date_query(birth_date: date) -> dict[str, dict[str, datetime]]:
    start = datetime.combine(birth_date, time.min)
    end = start + timedelta(days=1)
    return {"$gte": start, "$lt": end}


class AuthService:
    def __init__(self, repository: AuthRepository):
        self.repository = repository

    async def _get_attempt_doc(
        self, kind: str, key: str, *, now: datetime
    ) -> dict[str, Any] | None:
        doc = await self.repository.find_attempt(kind=kind, key=key)
        if not doc:
            return None

        window_start = _coerce_utc(doc.get("window_start"))
        lock_until = _coerce_utc(doc.get("lock_until"))
        if window_start is not None:
            doc["window_start"] = window_start
        if lock_until is not None:
            doc["lock_until"] = lock_until

        if window_start and window_start < _attempt_window_start(now):
            await self.repository.reset_attempt_window(attempt_id=doc["_id"], now=now)
            doc["count"] = 0
            doc["window_start"] = now
        return doc

    async def _increment_attempt(
        self, kind: str, key: str, *, now: datetime
    ) -> dict[str, Any]:
        doc = await self._get_attempt_doc(kind, key, now=now)
        if not doc:
            await self.repository.create_attempt(kind=kind, key=key, now=now)
            doc = await self.repository.find_attempt(kind=kind, key=key) or {
                "kind": kind,
                "key": key,
                "count": 0,
                "window_start": now,
                "lock_until": None,
                "updated_at": now,
            }

        update = {
            "$inc": {"count": 1},
            "$set": {"updated_at": now},
        }
        if kind == "cpf" and doc.get("count", 0) + 1 >= settings.cpf_attempt_limit:
            lock_until = now + timedelta(minutes=settings.cpf_lock_minutes)
            update["$set"]["lock_until"] = lock_until

        await self.repository.update_attempt(kind=kind, key=key, update=update)
        return await self.repository.find_attempt(kind=kind, key=key)

    async def _reset_attempts(self, kind: str, key: str) -> None:
        await self.repository.delete_attempt(kind=kind, key=key)

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
                window_end = cpf_doc["window_start"] + timedelta(
                    minutes=settings.rate_limit_window_minutes
                )
                retry_candidates.append(_seconds_until(window_end, now))

        if ip_doc and ip_doc.get("count", 0) >= settings.ip_attempt_limit:
            window_end = ip_doc["window_start"] + timedelta(
                minutes=settings.rate_limit_window_minutes
            )
            retry_candidates.append(_seconds_until(window_end, now))

        if retry_candidates:
            logger.warning(
                build_log_message(
                    "auth_rate_limited",
                    cpf=mask_cpf(cpf),
                    ip_ref=hash_identifier(ip),
                    retry_after=max(retry_candidates),
                )
            )
            raise AppError(
                status_code=429,
                code="AUTH_RATE_LIMITED",
                message="Too many authentication attempts",
                details={"retry_after": max(retry_candidates)},
            )

    async def authenticate_and_issue_token(
        self, *, cpf: str, birth_date: date, ip: str, request_id: str
    ):
        logger.info(
            build_log_message(
                "auth_attempt_started",
                request_id=request_id,
                cpf=mask_cpf(cpf),
                ip_ref=hash_identifier(ip),
            )
        )
        await self.check_rate_limit(cpf=cpf, ip=ip)

        student = await self.repository.find_student_by_cpf_and_birth_date(
            cpf=cpf,
            birth_date_query=_birth_date_query(birth_date),
        )
        if not student:
            await self._increment_attempt("cpf", cpf, now=datetime.now(UTC))
            await self._increment_attempt("ip", ip, now=datetime.now(UTC))
            logger.warning(
                build_log_message(
                    "auth_attempt_failed",
                    request_id=request_id,
                    cpf=mask_cpf(cpf),
                    ip_ref=hash_identifier(ip),
                    reason="invalid_credentials",
                )
            )
            raise AppError(
                status_code=401,
                code="INVALID_CREDENTIALS",
                message="CPF or birth date is invalid",
            )

        await self._reset_attempts("cpf", cpf)
        await self._reset_attempts("ip", ip)

        token, claims = create_access_token(
            student_id=str(student.get("student_id") or "") or str(student["_id"])
        )
        logger.info(
            build_log_message(
                "auth_attempt_succeeded",
                request_id=request_id,
                cpf=mask_cpf(cpf),
                ip_ref=hash_identifier(ip),
                student_ref=hash_identifier(
                    student.get("student_id") or student["_id"]
                ),
                jti_ref=hash_identifier(claims["jti"]),
                expires_at=datetime.fromtimestamp(claims["exp"], tz=UTC),
            )
        )

        return {"token": token, "claims": claims}

    async def revoke_token(self, *, jti: str, exp: int) -> None:
        expires_at = datetime.fromtimestamp(exp, tz=UTC)
        await self.repository.revoke_token(
            jti=jti,
            expires_at=expires_at,
            revoked_at=datetime.now(UTC),
        )
        logger.info(
            build_log_message(
                "auth_token_revoked",
                jti_ref=hash_identifier(jti),
                expires_at=expires_at,
            )
        )

    async def validate_access(
        self, *, token: str, assessment_id: str | None = None
    ) -> dict[str, Any]:
        payload = decode_access_token(token)
        logger.info(
            build_log_message(
                "auth_token_decoded",
                assessment_id=assessment_id,
                student_ref=hash_identifier(payload["sub"]),
                jti_ref=hash_identifier(payload["jti"]),
            )
        )

        try:
            revoked = await self.repository.find_revoked_token(jti=payload["jti"])
        except PyMongoError as exc:
            logger.exception(
                build_log_message(
                    "auth_revocation_store_unavailable",
                    assessment_id=assessment_id,
                    jti_ref=hash_identifier(payload["jti"]),
                )
            )
            raise AppError(
                status_code=503,
                code="REVOCATION_STORE_UNAVAILABLE",
                message="Revocation store unavailable",
            ) from exc

        if revoked:
            logger.warning(
                build_log_message(
                    "auth_token_revoked_access_denied",
                    assessment_id=assessment_id,
                    student_ref=hash_identifier(payload["sub"]),
                    jti_ref=hash_identifier(payload["jti"]),
                )
            )
            raise AppError(
                status_code=401, code="TOKEN_REVOKED", message="Token has been revoked"
            )

        if assessment_id:
            if not ObjectId.is_valid(assessment_id):
                logger.warning(
                    build_log_message(
                        "auth_access_invalid_assessment_id", assessment_id=assessment_id
                    )
                )
                raise AppError(
                    status_code=422, code="INVALID_ID", message="Invalid object ID"
                )
            record = await self.repository.find_assessment_by_id(
                assessment_id=ObjectId(assessment_id)
            )
            if not record:
                logger.warning(
                    build_log_message(
                        "auth_access_assessment_not_found",
                        assessment_id=assessment_id,
                        student_ref=hash_identifier(payload["sub"]),
                    )
                )
                raise AppError(
                    status_code=404,
                    code="ASSESSMENT_NOT_FOUND",
                    message="Assessment not found",
                )
            if str(record["student_id"]) != payload["sub"]:
                logger.warning(
                    build_log_message(
                        "auth_access_forbidden",
                        assessment_id=assessment_id,
                        student_ref=hash_identifier(payload["sub"]),
                        owner_ref=hash_identifier(record["student_id"]),
                    )
                )
                raise AppError(
                    status_code=403,
                    code="FORBIDDEN",
                    message="Assessment access denied",
                )

        logger.info(
            build_log_message(
                "auth_access_granted",
                assessment_id=assessment_id,
                student_ref=hash_identifier(payload["sub"]),
                jti_ref=hash_identifier(payload["jti"]),
            )
        )
        return payload
