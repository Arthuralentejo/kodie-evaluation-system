import logging

from fastapi import APIRouter, Depends, Request

from app.api.deps import AuthContext, get_auth_context
from app.db.mongo import get_db
from app.models.api import AuthRequest, AuthResponse, RevokeResponse
from app.services.auth_service import authenticate_and_issue_token, revoke_token

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger("kodie.auth")


@router.post("", response_model=AuthResponse)
async def auth(payload: AuthRequest, request: Request) -> AuthResponse:
    db = get_db()
    ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown").split(",")[0].strip()

    result = await authenticate_and_issue_token(
        cpf=payload.cpf,
        birth_date=payload.birth_date,
        ip=ip,
        db=db,
        logger=logger,
        request_id=request.state.request_id,
    )

    return AuthResponse(token=result["token"], assessment_id=result["assessment_id"])


@router.post("/revoke", response_model=RevokeResponse)
async def revoke(context: AuthContext = Depends(get_auth_context)) -> RevokeResponse:
    db = get_db()
    # Token self-revocation is used for emergency session invalidation.
    await revoke_token(jti=context.jti, exp=context.exp, db=db)
    return RevokeResponse(status="revoked")
