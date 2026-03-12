from fastapi import APIRouter, Depends

from app.api.deps import AuthContext, get_auth_context
from app.db.mongo import get_db
from app.models.api import QuestionResponse, SubmitResponse, UpsertAnswerRequest
from app.services.assessment_service import get_questions_for_assessment, submit_assessment, upsert_answer

router = APIRouter(prefix="/assessments", tags=["assessments"])


@router.get("/{assessment_id}/questions", response_model=list[QuestionResponse])
async def get_questions(assessment_id: str, _: AuthContext = Depends(get_auth_context)):
    db = get_db()
    return await get_questions_for_assessment(assessment_id=assessment_id, db=db)


@router.patch("/{assessment_id}/answers")
async def patch_answer(assessment_id: str, payload: UpsertAnswerRequest, _: AuthContext = Depends(get_auth_context)):
    db = get_db()
    await upsert_answer(
        assessment_id=assessment_id,
        question_id=payload.question_id,
        selected_option=payload.selected_option,
        db=db,
    )
    return {"status": "ok"}


@router.post("/{assessment_id}/submit", response_model=SubmitResponse)
async def submit(assessment_id: str, _: AuthContext = Depends(get_auth_context)):
    db = get_db()
    result = await submit_assessment(assessment_id=assessment_id, db=db)
    return SubmitResponse(**result)
