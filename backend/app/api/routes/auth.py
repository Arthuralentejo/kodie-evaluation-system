import logging

from fastapi import APIRouter, Depends, Request

from app.api.deps import AuthContext, get_auth_context, get_auth_service
from app.models.api import AuthRequest, AuthResponse, RevokeResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger("kodie.auth")


@router.post("", response_model=AuthResponse)
async def auth(
    payload: AuthRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthResponse:
    ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown").split(",")[0].strip()

    result = await auth_service.authenticate_and_issue_token(
        cpf=payload.cpf,
        birth_date=payload.birth_date,
        ip=ip,
        request_id=request.state.request_id,
    )

    return AuthResponse(token=result["token"])


@router.post("/revoke", response_model=RevokeResponse)
async def revoke(
    context: AuthContext = Depends(get_auth_context),
    auth_service: AuthService = Depends(get_auth_service),
) -> RevokeResponse:
    # Token self-revocation is used for emergency session invalidation.
    await auth_service.revoke_token(jti=context.jti, exp=context.exp)
    return RevokeResponse(status="revoked")
