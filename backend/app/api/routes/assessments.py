from fastapi import APIRouter, Depends, Query, Request

from app.api.deps import AuthContext, get_assessment_service, get_auth_context
from app.core.logger import build_log_message, get_logger, hash_identifier
from app.models.api import (
    AssessmentSummaryResponse,
    CreateAssessmentRequest,
    CreateAssessmentResponse,
    QuestionResponse,
    SubmitResponse,
    UpsertAnswerRequest,
)
from app.services.assessment_service import AssessmentService

logger = get_logger("kodie.api.assessments")
router = APIRouter(
    prefix="/assessments",
    tags=["assessments"],
    dependencies=[Depends(get_auth_context)],
)


@router.get("/current", response_model=AssessmentSummaryResponse)
async def get_current_assessment(
    request: Request,
    context: AuthContext = Depends(get_auth_context),
    assessment_service: AssessmentService = Depends(get_assessment_service),
):
    logger.info(
        build_log_message(
            "assessment_current_requested",
            request_id=request.state.request_id,
            student_ref=hash_identifier(context.student_id),
        )
    )
    result = await assessment_service.get_current_assessment(student_id=context.student_id)
    logger.info(
        build_log_message(
            "assessment_current_completed",
            request_id=request.state.request_id,
            student_ref=hash_identifier(context.student_id),
            status=result["status"],
            assessment_id=result["assessment_id"],
            history_count=len(result.get("assessments", [])),
        )
    )
    return AssessmentSummaryResponse(**result)


@router.post("", response_model=CreateAssessmentResponse)
async def create_assessment(
    payload: CreateAssessmentRequest,
    request: Request,
    context: AuthContext = Depends(get_auth_context),
    assessment_service: AssessmentService = Depends(get_assessment_service),
):
    logger.info(
        build_log_message(
            "assessment_create_requested",
            request_id=request.state.request_id,
            student_ref=hash_identifier(context.student_id),
            assessment_type=payload.assessment_type.value,
        )
    )
    result = await assessment_service.create_assessment(
        student_id=context.student_id,
        assessment_type=payload.assessment_type.value,
    )
    logger.info(
        build_log_message(
            "assessment_create_completed",
            request_id=request.state.request_id,
            student_ref=hash_identifier(context.student_id),
            assessment_id=result["assessment_id"],
            assessment_type=result["assessment_type"],
            status=result["status"],
        )
    )
    return CreateAssessmentResponse(**result)


@router.get("/{assessment_id}/questions", response_model=list[QuestionResponse])
async def get_questions(
    assessment_id: str,
    request: Request,
    quantity: int = Query(default=20, ge=1),
    assessment_service: AssessmentService = Depends(get_assessment_service),
):
    logger.info(
        build_log_message(
            "assessment_questions_requested",
            request_id=request.state.request_id,
            assessment_id=assessment_id,
            quantity=quantity,
        )
    )
    response = await assessment_service.get_questions_for_assessment(
        assessment_id=assessment_id,
        quantity=quantity,
        request_id=request.state.request_id,
    )
    logger.info(
        build_log_message(
            "assessment_questions_completed",
            request_id=request.state.request_id,
            assessment_id=assessment_id,
            returned_count=len(response),
        )
    )
    return response


@router.patch("/{assessment_id}/answers")
async def patch_answer(
    assessment_id: str,
    payload: UpsertAnswerRequest,
    request: Request,
    assessment_service: AssessmentService = Depends(get_assessment_service),
):
    logger.info(
        build_log_message(
            "assessment_answer_request_received",
            request_id=request.state.request_id,
            assessment_id=assessment_id,
            question_id=payload.question_id,
            selected_option=payload.selected_option,
        )
    )
    await assessment_service.upsert_answer(
        assessment_id=assessment_id,
        question_id=payload.question_id,
        selected_option=payload.selected_option,
        request_id=request.state.request_id,
    )
    logger.info(
        build_log_message(
            "assessment_answer_request_completed",
            request_id=request.state.request_id,
            assessment_id=assessment_id,
            question_id=payload.question_id,
        )
    )
    return {"status": "ok"}


@router.post("/{assessment_id}/submit", response_model=SubmitResponse)
async def submit(
    assessment_id: str,
    request: Request,
    assessment_service: AssessmentService = Depends(get_assessment_service),
):
    logger.info(
        build_log_message(
            "assessment_submit_requested",
            request_id=request.state.request_id,
            assessment_id=assessment_id,
        )
    )
    result = await assessment_service.submit_assessment(
        assessment_id=assessment_id,
        request_id=request.state.request_id,
    )
    logger.info(
        build_log_message(
            "assessment_submit_completed",
            request_id=request.state.request_id,
            assessment_id=assessment_id,
            status=result["status"],
            completed_at=result["completed_at"],
        )
    )
    return SubmitResponse(**result)
