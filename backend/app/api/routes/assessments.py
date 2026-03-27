from fastapi import APIRouter, Depends, Query, Request

from app.api.deps import AuthContext, get_assessment_service, get_auth_context
from app.models.api import (
    AssessmentSummaryResponse,
    CreateAssessmentResponse,
    QuestionResponse,
    SubmitResponse,
    UpsertAnswerRequest,
)
from app.services.assessment_service import AssessmentService

router = APIRouter(
    prefix="/assessments",
    tags=["assessments"],
    dependencies=[Depends(get_auth_context)],
)


@router.get("/current", response_model=AssessmentSummaryResponse)
async def get_current_assessment(
    context: AuthContext = Depends(get_auth_context),
    assessment_service: AssessmentService = Depends(get_assessment_service),
):
    result = await assessment_service.get_current_assessment(student_id=context.student_id)
    return AssessmentSummaryResponse(**result)


@router.post("", response_model=CreateAssessmentResponse)
async def create_assessment(
    context: AuthContext = Depends(get_auth_context),
    assessment_service: AssessmentService = Depends(get_assessment_service),
):
    result = await assessment_service.create_assessment(student_id=context.student_id)
    return CreateAssessmentResponse(**result)


@router.get("/{assessment_id}/questions", response_model=list[QuestionResponse])
async def get_questions(
    assessment_id: str,
    request: Request,
    quantity: int = Query(default=20, ge=1),
    assessment_service: AssessmentService = Depends(get_assessment_service),
):
    return await assessment_service.get_questions_for_assessment(
        assessment_id=assessment_id,
        quantity=quantity,
        request_id=request.state.request_id,
    )


@router.patch("/{assessment_id}/answers")
async def patch_answer(
    assessment_id: str,
    payload: UpsertAnswerRequest,
    request: Request,
    assessment_service: AssessmentService = Depends(get_assessment_service),
):
    await assessment_service.upsert_answer(
        assessment_id=assessment_id,
        question_id=payload.question_id,
        selected_option=payload.selected_option,
        request_id=request.state.request_id,
    )
    return {"status": "ok"}


@router.post("/{assessment_id}/submit", response_model=SubmitResponse)
async def submit(
    assessment_id: str,
    request: Request,
    assessment_service: AssessmentService = Depends(get_assessment_service),
):
    result = await assessment_service.submit_assessment(
        assessment_id=assessment_id,
        request_id=request.state.request_id,
    )
    return SubmitResponse(**result)
