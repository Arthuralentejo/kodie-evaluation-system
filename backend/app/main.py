import uuid
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes.assessments import router as assessments_router
from app.api.routes.auth import router as auth_router
from app.api.routes.health import router as health_router
from app.core.config import settings
from app.core.errors import AppError
from app.db.indexes import ensure_indexes
from app.db.mongo import close_client, get_db
from app.services.assessment_service import AssessmentService
from app.services.auth_service import AuthService


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = get_db()
    await ensure_indexes()
    try:
        yield {
            "assessment_service": AssessmentService(db=db),
            "auth_service": AuthService(db=db),
        }
    finally:
        await close_client()


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["x-request-id", "Retry-After"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["x-request-id"] = request_id
    return response


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    details = dict(exc.details)
    retry_after = details.pop("retry_after", None)

    response = JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.code,
            "message": exc.message,
            "request_id": request.state.request_id,
            "details": details or {},
        },
    )
    if retry_after is not None:
        response.headers["Retry-After"] = str(retry_after)
    return response


@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, _: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "code": "INTERNAL_ERROR",
            "message": "Unexpected error",
            "request_id": request.state.request_id,
            "details": {},
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "code": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "request_id": request.state.request_id,
            "details": {"errors": jsonable_encoder(exc.errors())},
        },
    )


app.include_router(health_router)
app.include_router(auth_router)
app.include_router(assessments_router)
