from dataclasses import dataclass

from bson import ObjectId
from pymongo.errors import PyMongoError
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.errors import AppError
from app.core.security import decode_access_token
from app.db.collections import assessments_collection, denylist_collection
from app.db.mongo import get_db

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class AuthContext:
    student_id: str
    assessment_id: str
    jti: str
    exp: int


async def get_auth_context(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AuthContext:
    if credentials is None:
        raise AppError(status_code=401, code="MISSING_TOKEN", message="Authorization token is required")

    payload = decode_access_token(credentials.credentials)

    db = get_db()
    try:
        revoked = await denylist_collection(db).find_one({"jti": payload["jti"]})
    except PyMongoError as exc:
        raise AppError(status_code=503, code="REVOCATION_STORE_UNAVAILABLE", message="Revocation store unavailable") from exc

    if revoked:
        raise AppError(status_code=401, code="TOKEN_REVOKED", message="Token has been revoked")

    assessment_id = request.path_params.get("assessment_id")
    if assessment_id and assessment_id != payload["assessment_id"]:
        raise AppError(status_code=403, code="FORBIDDEN", message="Assessment access denied")

    if assessment_id:
        if not ObjectId.is_valid(assessment_id):
            raise AppError(status_code=422, code="INVALID_ID", message="Invalid object ID")
        record = await assessments_collection(db).find_one({"_id": ObjectId(assessment_id)})
        if not record:
            raise AppError(status_code=404, code="ASSESSMENT_NOT_FOUND", message="Assessment not found")
        if str(record["student_id"]) != payload["sub"]:
            raise AppError(status_code=403, code="FORBIDDEN", message="Assessment access denied")

    return AuthContext(
        student_id=payload["sub"],
        assessment_id=payload["assessment_id"],
        jti=payload["jti"],
        exp=payload["exp"],
    )
