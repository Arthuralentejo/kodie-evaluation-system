from fastapi import APIRouter, Depends, Query

from app.api.deps import get_assessment_service, get_auth_context
from app.models.api import QuestionResponse, SubmitResponse, UpsertAnswerRequest
from app.services.assessment_service import AssessmentService

router = APIRouter(
    prefix="/assessments",
    tags=["assessments"],
    dependencies=[Depends(get_auth_context)],
)


@router.get("/{assessment_id}/questions", response_model=list[QuestionResponse])
async def get_questions(
    assessment_id: str,
    quantity: int | None = Query(default=None, ge=1),
    assessment_service: AssessmentService = Depends(get_assessment_service),
):
    return await assessment_service.get_questions_for_assessment(assessment_id=assessment_id, quantity=quantity)


@router.patch("/{assessment_id}/answers")
async def patch_answer(
    assessment_id: str,
    payload: UpsertAnswerRequest,
    assessment_service: AssessmentService = Depends(get_assessment_service),
):
    await assessment_service.upsert_answer(
        assessment_id=assessment_id,
        question_id=payload.question_id,
        selected_option=payload.selected_option,
    )
    return {"status": "ok"}


@router.post("/{assessment_id}/submit", response_model=SubmitResponse)
async def submit(
    assessment_id: str,
    assessment_service: AssessmentService = Depends(get_assessment_service),
):
    result = await assessment_service.submit_assessment(assessment_id=assessment_id)
    return SubmitResponse(**result)
