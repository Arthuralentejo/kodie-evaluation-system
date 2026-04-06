import uuid
from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes.admin import router as admin_router
from app.api.routes.assessments import router as assessments_router
from app.api.routes.auth import router as auth_router
from app.api.routes.health import router as health_router
from app.core.config import settings
from app.core.errors import AppError
from app.core.logger import build_log_message, configure_logging, get_logger
from app.db.collections import assessments_collection, questions_collection
from app.db.indexes import ensure_indexes
from app.db.mongo import close_client, get_db
from app.repositories.assessment_repository import AssessmentRepository
from app.repositories.auth_repository import AuthRepository
from app.services.analytics_service import AnalyticsService
from app.services.assessment_service import AssessmentService
from app.services.auth_service import AuthService
from app.services.evaluation_engine import EvaluationEngine
from app.services.ranking_service import RankingService

configure_logging()
http_logger = get_logger("kodie.http")


@asynccontextmanager
async def lifespan(app: FastAPI):
    http_logger.info(
        build_log_message(
            "application_startup_started", app_name=settings.app_name, env=settings.env
        )
    )
    db = get_db()
    auth_repository = AuthRepository(db=db)
    assessment_repository = AssessmentRepository(
        collection=assessments_collection(db),
        questions_collection=questions_collection(db),
    )
    await ensure_indexes()
    evaluation_engine = EvaluationEngine()
    ranking_service = RankingService(repository=assessment_repository)
    analytics_service = AnalyticsService(repository=assessment_repository)
    try:
        http_logger.info(
            build_log_message(
                "application_startup_completed",
                app_name=settings.app_name,
                env=settings.env,
            )
        )
        yield {
            "assessment_service": AssessmentService(
                repository=assessment_repository, evaluation_engine=evaluation_engine
            ),
            "auth_service": AuthService(repository=auth_repository),
            "ranking_service": ranking_service,
            "analytics_service": analytics_service,
            "assessment_repository": assessment_repository,
        }
    finally:
        http_logger.info(
            build_log_message(
                "application_shutdown_started",
                app_name=settings.app_name,
                env=settings.env,
            )
        )
        await close_client()
        http_logger.info(
            build_log_message(
                "application_shutdown_completed",
                app_name=settings.app_name,
                env=settings.env,
            )
        )


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
    started_at = perf_counter()
    response = await call_next(request)
    response.headers["x-request-id"] = request_id
    http_logger.info(
        build_log_message(
            "request_completed",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round((perf_counter() - started_at) * 1000, 2),
        )
    )
    return response


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    details = dict(exc.details)
    retry_after = details.pop("retry_after", None)
    http_logger.warning(
        build_log_message(
            "app_error",
            request_id=request.state.request_id,
            method=request.method,
            path=request.url.path,
            status_code=exc.status_code,
            code=exc.code,
            details=details,
        )
    )

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
async def unexpected_error_handler(request: Request, exc: Exception):
    http_logger.exception(
        build_log_message(
            "unexpected_error",
            request_id=request.state.request_id,
            method=request.method,
            path=request.url.path,
        )
    )
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
    http_logger.warning(
        build_log_message(
            "validation_error",
            request_id=request.state.request_id,
            method=request.method,
            path=request.url.path,
            errors=jsonable_encoder(exc.errors()),
        )
    )
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
app.include_router(admin_router)
