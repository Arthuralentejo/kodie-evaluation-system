from dataclasses import dataclass

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.errors import AppError
from app.services.assessment_service import AssessmentService
from app.services.auth_service import AuthService

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class AuthContext:
    student_id: str
    assessment_id: str
    jti: str
    exp: int


def get_auth_service(request: Request) -> AuthService:
    return request.state.auth_service


def get_assessment_service(request: Request) -> AssessmentService:
    return request.state.assessment_service


async def get_auth_context(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthContext:
    if credentials is None:
        raise AppError(
            status_code=401,
            code="MISSING_TOKEN",
            message="Authorization token is required",
        )

    assessment_id = request.path_params.get("assessment_id")
    payload = await auth_service.validate_access(
        token=credentials.credentials, assessment_id=assessment_id
    )

    return AuthContext(
        student_id=payload["sub"],
        assessment_id=payload["assessment_id"],
        jti=payload["jti"],
        exp=payload["exp"],
    )
