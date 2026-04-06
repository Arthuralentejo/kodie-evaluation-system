from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from app.api.deps import get_admin_context, get_analytics_service, get_ranking_service
from app.core.errors import AppError
from app.core.logger import build_log_message, get_logger
from app.models.api import (
    AdminResultDetail,
    AdminResultSummary,
    AnalyticsResult,
    RankingPage,
)
from app.repositories.assessment_repository import AssessmentRepository
from app.services.analytics_service import AnalyticsService
from app.services.ranking_service import RankingService

router = APIRouter(
    prefix="/admin", tags=["admin"], dependencies=[Depends(get_admin_context)]
)
logger = get_logger("kodie.api.admin")


def _get_assessment_repository(request: Request) -> AssessmentRepository:
    return request.state.assessment_repository


AssessmentRepoDep = Annotated[AssessmentRepository, Depends(_get_assessment_repository)]
AnalyticsServiceDep = Annotated[AnalyticsService, Depends(get_analytics_service)]
RankingServiceDep = Annotated[RankingService, Depends(get_ranking_service)]


@router.get("/results", response_model=list[AdminResultSummary])
async def list_results(
    request: Request,
    repo: AssessmentRepoDep,
    assessment_type: str | None = Query(default=None),
    classification_value: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    logger.info(
        build_log_message(
            "admin_results_requested",
            request_id=request.state.request_id,
            assessment_type=assessment_type,
            classification_value=classification_value,
            page=page,
            page_size=page_size,
        )
    )
    docs, total = await repo.list_completed_assessments(
        assessment_type=assessment_type,
        classification_value=classification_value,
        page=page,
        page_size=page_size,
    )
    results = []
    for doc in docs:
        er = doc.get("evaluation_result")
        results.append(
            AdminResultSummary(
                assessment_id=str(doc["_id"]),
                student_id=doc.get("student_id", ""),
                assessment_type=doc.get("assessment_type", ""),
                score_total=er.get("score_total") if er else None,
                score_max=er.get("score_max") if er else None,
                score_percent=er.get("score_percent") if er else None,
                performance_by_level=er.get("performance_by_level") if er else None,
                classification_kind=er.get("classification_kind") if er else None,
                classification_value=er.get("classification_value") if er else None,
                duration_seconds=er.get("duration_seconds") if er else None,
                completed_at=doc["completed_at"].isoformat()
                if doc.get("completed_at")
                else "",
            )
        )
    logger.info(
        build_log_message(
            "admin_results_completed",
            request_id=request.state.request_id,
            assessment_type=assessment_type,
            classification_value=classification_value,
            page=page,
            page_size=page_size,
            total=total,
            returned_count=len(results),
        )
    )
    return results


@router.get("/results/{assessment_id}", response_model=AdminResultDetail)
async def get_result_detail(
    request: Request,
    assessment_id: str,
    repo: AssessmentRepoDep,
):
    logger.info(
        build_log_message(
            "admin_result_detail_requested",
            request_id=request.state.request_id,
            assessment_id=assessment_id,
        )
    )
    from bson import ObjectId

    if not ObjectId.is_valid(assessment_id):
        logger.warning(
            build_log_message(
                "admin_result_detail_invalid_assessment_id",
                request_id=request.state.request_id,
                assessment_id=assessment_id,
            )
        )
        raise AppError(
            status_code=404, code="ASSESSMENT_NOT_FOUND", message="Assessment not found"
        )
    doc = await repo.find_assessment_by_id(assessment_id=ObjectId(assessment_id))
    if not doc or doc.get("status") != "COMPLETED":
        logger.warning(
            build_log_message(
                "admin_result_detail_not_found",
                request_id=request.state.request_id,
                assessment_id=assessment_id,
            )
        )
        raise AppError(
            status_code=404, code="ASSESSMENT_NOT_FOUND", message="Assessment not found"
        )
    er = doc.get("evaluation_result")
    result = AdminResultDetail(
        assessment_id=str(doc["_id"]),
        student_id=doc.get("student_id", ""),
        assessment_type=doc.get("assessment_type", ""),
        score_total=er.get("score_total") if er else None,
        score_max=er.get("score_max") if er else None,
        score_percent=er.get("score_percent") if er else None,
        performance_by_level=er.get("performance_by_level") if er else None,
        classification_kind=er.get("classification_kind") if er else None,
        classification_value=er.get("classification_value") if er else None,
        duration_seconds=er.get("duration_seconds") if er else None,
        completed_at=doc["completed_at"].isoformat() if doc.get("completed_at") else "",
        question_results=er.get("question_results") if er else None,
    )
    logger.info(
        build_log_message(
            "admin_result_detail_completed",
            request_id=request.state.request_id,
            assessment_id=assessment_id,
            assessment_type=result.assessment_type,
            classification_value=result.classification_value,
        )
    )
    return result


@router.get("/analytics", response_model=AnalyticsResult)
async def get_analytics(
    request: Request,
    analytics_service: AnalyticsServiceDep,
    assessment_type: str | None = Query(default=None),
):
    logger.info(
        build_log_message(
            "admin_analytics_requested",
            request_id=request.state.request_id,
            assessment_type=assessment_type,
        )
    )
    result = await analytics_service.get_analytics(assessment_type=assessment_type)
    logger.info(
        build_log_message(
            "admin_analytics_completed",
            request_id=request.state.request_id,
            assessment_type=assessment_type,
            classification_bucket_count=len(result.classification_distribution),
            score_bucket_count=len(result.score_distribution_normalized),
            level_count=len(result.level_accuracy),
        )
    )
    return result


@router.get("/ranking/by-type", response_model=RankingPage)
async def ranking_by_type(
    request: Request,
    ranking_service: RankingServiceDep,
    assessment_type: str = Query(...),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    logger.info(
        build_log_message(
            "admin_ranking_by_type_requested",
            request_id=request.state.request_id,
            assessment_type=assessment_type,
            page=page,
            page_size=page_size,
        )
    )
    result = await ranking_service.rank_by_type(
        assessment_type=assessment_type, page=page, page_size=page_size
    )
    logger.info(
        build_log_message(
            "admin_ranking_by_type_completed",
            request_id=request.state.request_id,
            assessment_type=assessment_type,
            page=page,
            page_size=page_size,
            total=result.total,
            returned_count=len(result.entries),
        )
    )
    return result


@router.get("/ranking/global", response_model=RankingPage)
async def ranking_global(
    request: Request,
    ranking_service: RankingServiceDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    logger.info(
        build_log_message(
            "admin_ranking_global_requested",
            request_id=request.state.request_id,
            page=page,
            page_size=page_size,
        )
    )
    result = await ranking_service.rank_global(page=page, page_size=page_size)
    logger.info(
        build_log_message(
            "admin_ranking_global_completed",
            request_id=request.state.request_id,
            page=page,
            page_size=page_size,
            total=result.total,
            returned_count=len(result.entries),
        )
    )
    return result
