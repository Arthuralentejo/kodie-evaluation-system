from dataclasses import dataclass

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.core.errors import AppError
from app.core.logger import build_log_message, get_logger, hash_identifier
from app.services.assessment_service import AssessmentService
from app.services.auth_service import AuthService

bearer_scheme = HTTPBearer(auto_error=False)
logger = get_logger("kodie.api.deps")


@dataclass
class AuthContext:
    student_id: str
    jti: str
    exp: int


def get_auth_service(request: Request) -> AuthService:
    return request.state.auth_service


def get_assessment_service(request: Request) -> AssessmentService:
    return request.state.assessment_service


def get_ranking_service(request: Request):
    return request.state.ranking_service


def get_analytics_service(request: Request):
    return request.state.analytics_service


async def get_admin_context(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> None:
    if credentials is None:
        logger.warning(build_log_message("admin_access_denied", request_id=request.state.request_id, reason="missing_token"))
        raise AppError(status_code=401, code="UNAUTHORIZED", message="Admin token required")
    if credentials.credentials != settings.admin_token:
        logger.warning(build_log_message("admin_access_denied", request_id=request.state.request_id, reason="invalid_token"))
        raise AppError(status_code=403, code="FORBIDDEN", message="Invalid admin token")
    logger.info(build_log_message("admin_access_granted", request_id=request.state.request_id))


async def get_auth_context(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthContext:
    if credentials is None:
        logger.warning(build_log_message("auth_context_missing_token", request_id=request.state.request_id))
        raise AppError(
            status_code=401,
            code="MISSING_TOKEN",
            message="Authorization token is required",
        )

    assessment_id = request.path_params.get("assessment_id")
    payload = await auth_service.validate_access(
        token=credentials.credentials, assessment_id=assessment_id
    )
    logger.info(
        build_log_message(
            "auth_context_resolved",
            request_id=request.state.request_id,
            assessment_id=assessment_id,
            student_ref=hash_identifier(payload["sub"]),
            jti_ref=hash_identifier(payload["jti"]),
        )
    )

    return AuthContext(
        student_id=payload["sub"],
        jti=payload["jti"],
        exp=payload["exp"],
    )
