from datetime import UTC, datetime
import hashlib
import random

from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from app.core.config import settings
from app.core.errors import AppError
from app.core.logger import build_log_message, get_logger, hash_identifier
from app.models.domain import AssessmentType
from app.repositories.assessment_repository import AssessmentRepository
from app.services.evaluation_engine import EvaluationEngine
from app.services.question_selection import build_assigned_question_ids, build_geral_question_ids

logger = get_logger("kodie.assessment")


def _ensure_object_id(value: str, code: str = "INVALID_ID") -> ObjectId:
    if not ObjectId.is_valid(value):
        raise AppError(status_code=422, code=code, message="Invalid object ID")
    return ObjectId(value)


def deterministic_shuffle_options(*, assessment_id: str, question_id: str, options: list[dict]) -> list[dict]:
    seed = f"{assessment_id}:{question_id}:{settings.shuffle_seed_version}".encode("utf-8")
    seed_int = int(hashlib.sha256(seed).hexdigest(), 16)
    rnd = random.Random(seed_int)
    shuffled = [dict(item) for item in options]
    rnd.shuffle(shuffled)
    return shuffled


class AssessmentService:
    def __init__(self, repository: AssessmentRepository, evaluation_engine: EvaluationEngine | None = None):
        self.repository = repository
        self.evaluation_engine = evaluation_engine or EvaluationEngine()

    async def get_current_assessment(self, *, student_id: str):
        logger.info(build_log_message("assessment_current_lookup_started", student_ref=hash_identifier(student_id)))
        # Query 1: single active (non-archived) assessment
        active = await self.repository.find_active_assessment_by_student(student_id=student_id)

        # Query 2: ALL completed assessments (including archived) for history
        completed_history = await self.repository.find_all_completed_assessments_by_student(student_id=student_id)
        assessments = [
            {
                "assessment_id": str(a["_id"]),
                "assessment_type": a.get("assessment_type", "iniciante"),
                "completed_at": a["completed_at"].isoformat(),
            }
            for a in completed_history
        ]

        if active is not None:
            logger.info(
                build_log_message(
                    "assessment_current_lookup_completed",
                    student_ref=hash_identifier(student_id),
                    status=active["status"],
                    assessment_id=str(active["_id"]),
                    history_count=len(assessments),
                )
            )
            return {
                "status": active["status"],
                "assessment_id": str(active["_id"]),
                "completed_at": active["completed_at"].isoformat() if active.get("completed_at") else None,
                "assessment_type": active.get("assessment_type", "iniciante"),
                "assessments": assessments,
            }

        logger.info(
            build_log_message(
                "assessment_current_lookup_completed",
                student_ref=hash_identifier(student_id),
                status="NONE",
                history_count=len(assessments),
            )
        )
        return {"status": "NONE", "assessment_id": None, "completed_at": None, "assessment_type": None, "assessments": assessments}

    async def create_assessment(self, *, student_id: str, assessment_type: str):
        logger.info(
            build_log_message(
                "assessment_create_started",
                student_ref=hash_identifier(student_id),
                assessment_type=assessment_type,
            )
        )
        # Validate assessment_type
        try:
            AssessmentType(assessment_type)
        except ValueError:
            logger.warning(
                build_log_message(
                    "assessment_create_invalid_type",
                    student_ref=hash_identifier(student_id),
                    assessment_type=assessment_type,
                )
            )
            raise AppError(status_code=422, code="INVALID_ASSESSMENT_TYPE", message="Tipo de avaliação inválido.")

        # Step 1: Check completed history (all completed, including archived) for this assessment_type
        completed_history = await self.repository.find_all_completed_assessments_by_student(student_id=student_id)
        if any(a.get("assessment_type") == assessment_type for a in completed_history):
            logger.warning(
                build_log_message(
                    "assessment_create_already_completed",
                    student_ref=hash_identifier(student_id),
                    assessment_type=assessment_type,
                    completed_history_count=len(completed_history),
                )
            )
            raise AppError(status_code=409, code="LEVEL_ALREADY_COMPLETED",
                           message="Este nível já foi concluído e não pode ser iniciado novamente.")

        # Step 2: Fetch the single active (non-archived) assessment
        active = await self.repository.find_active_assessment_by_student(student_id=student_id)

        # Step 3: Handle based on active state
        if active is not None:
            if active.get("assessment_type") == assessment_type and active["status"] == "DRAFT":
                logger.info(
                    build_log_message(
                        "assessment_create_idempotent",
                        student_ref=hash_identifier(student_id),
                        assessment_type=assessment_type,
                        assessment_id=str(active["_id"]),
                    )
                )
                # Idempotent: same assessment_type DRAFT — return it
                return {"assessment_id": str(active["_id"]), "status": "DRAFT", "assessment_type": assessment_type}

            # Different assessment_type (or same type COMPLETED — already handled above): archive it
            await self.repository.archive_assessment(assessment_id=active["_id"])
            logger.info(
                build_log_message(
                    "assessment_create_archived_previous",
                    student_ref=hash_identifier(student_id),
                    previous_assessment_id=str(active["_id"]),
                    previous_assessment_type=active.get("assessment_type"),
                    previous_status=active.get("status"),
                )
            )

        # Step 4: Create new DRAFT
        if assessment_type == AssessmentType.GERAL.value:
            question_docs = await self.repository.list_questions_for_geral()
            assigned_question_ids = build_geral_question_ids(question_docs)
        else:
            question_docs = await self.repository.list_questions_for_level(level=assessment_type)
            assigned_question_ids = build_assigned_question_ids(question_docs)
        if not assigned_question_ids:
            logger.warning(
                build_log_message(
                    "assessment_create_no_questions",
                    student_ref=hash_identifier(student_id),
                    assessment_type=assessment_type,
                )
            )
            raise AppError(status_code=409, code="NO_QUESTIONS_FOR_LEVEL",
                           message="Não há questões disponíveis para o nível selecionado.")
        logger.info(
            build_log_message(
                "assessment_create_questions_selected",
                student_ref=hash_identifier(student_id),
                assessment_type=assessment_type,
                candidate_count=len(question_docs),
                assigned_count=len(assigned_question_ids),
            )
        )

        now = datetime.now(UTC)
        try:
            created = await self.repository.create_assessment(
                student_id=student_id,
                assigned_question_ids=assigned_question_ids,
                assessment_type=assessment_type,
                now=now,
            )
        except DuplicateKeyError:
            active = await self.repository.find_active_assessment_by_student(student_id=student_id)
            if active:
                logger.warning(
                    build_log_message(
                        "assessment_create_race_reused_active",
                        student_ref=hash_identifier(student_id),
                        assessment_type=assessment_type,
                        assessment_id=str(active["_id"]),
                    )
                )
                return {"assessment_id": str(active["_id"]), "status": "DRAFT", "assessment_type": assessment_type}
            logger.exception(
                build_log_message(
                    "assessment_create_failed_after_duplicate_key",
                    student_ref=hash_identifier(student_id),
                    assessment_type=assessment_type,
                )
            )
            raise AppError(status_code=503, code="DRAFT_BOOTSTRAP_FAILED", message="Failed to create assessment")

        logger.info(
            build_log_message(
                "assessment_create_completed",
                student_ref=hash_identifier(student_id),
                assessment_id=str(created["_id"]),
                assessment_type=assessment_type,
                assigned_count=len(assigned_question_ids),
            )
        )
        return {"assessment_id": str(created["_id"]), "status": "DRAFT", "assessment_type": assessment_type}

    async def get_questions_for_assessment(
        self,
        *,
        assessment_id: str,
        quantity: int | None = None,
        request_id: str | None = None,
    ):
        assess_oid = _ensure_object_id(assessment_id)
        logger.info(build_log_message("assessment_questions_load_started", request_id=request_id, assessment_id=assessment_id, quantity=quantity))
        assessment = await self.repository.find_assessment_by_id(assessment_id=assess_oid)
        if not assessment:
            logger.warning(build_log_message("assessment_questions_load_not_found", request_id=request_id, assessment_id=assessment_id))
            raise AppError(status_code=404, code="ASSESSMENT_NOT_FOUND", message="Assessment not found")

        assigned_question_ids = assessment.get("assigned_question_ids", [])
        question_docs = await self.repository.find_questions_by_ids(question_ids=assigned_question_ids)
        question_by_id = {question["_id"]: question for question in question_docs}
        ordered_questions = [question_by_id[question_id] for question_id in assigned_question_ids if question_id in question_by_id]
        if quantity is not None:
            ordered_questions = ordered_questions[:quantity]

        answer_by_question = {
            str(item["question_id"]): item["selected_option"]
            for item in assessment.get("answers", [])
        }

        response = []
        for q in ordered_questions:
            qid = str(q["_id"])
            response.append(
                {
                    "id": qid,
                    "statement": q["statement"],
                    "options": deterministic_shuffle_options(
                        assessment_id=assessment_id,
                        question_id=qid,
                        options=q["options"],
                    ),
                    "selected_option": answer_by_question.get(qid),
                }
            )

        logger.info(build_log_message(
            "assessment_questions_loaded",
            request_id=request_id,
            assessment_id=assessment_id,
            stored_assigned_count=len(assigned_question_ids),
            returned_count=len(response),
            quantity=quantity,
            answered_count=len(answer_by_question),
        ))
        return response

    async def upsert_answer(
        self,
        *,
        assessment_id: str,
        question_id: str,
        selected_option: str,
        request_id: str | None = None,
    ):
        assess_oid = _ensure_object_id(assessment_id)
        question_oid = _ensure_object_id(question_id, code="INVALID_QUESTION_ID")
        logger.info(
            build_log_message(
                "assessment_answer_upsert_started",
                request_id=request_id,
                assessment_id=assessment_id,
                question_id=question_id,
                selected_option=selected_option,
            )
        )

        assessment = await self.repository.find_assessment_by_id(assessment_id=assess_oid)
        if not assessment:
            logger.warning(build_log_message("assessment_answer_upsert_assessment_not_found", request_id=request_id, assessment_id=assessment_id))
            raise AppError(status_code=404, code="ASSESSMENT_NOT_FOUND", message="Assessment not found")
        if question_oid not in assessment.get("assigned_question_ids", []):
            logger.warning(
                build_log_message(
                    "assessment_answer_upsert_question_not_assigned",
                    request_id=request_id,
                    assessment_id=assessment_id,
                    question_id=question_id,
                )
            )
            raise AppError(status_code=404, code="QUESTION_NOT_FOUND", message="Question not assigned to assessment")

        question = await self.repository.find_question_by_id(question_id=question_oid)
        if not question:
            logger.warning(
                build_log_message(
                    "assessment_answer_upsert_question_not_found",
                    request_id=request_id,
                    assessment_id=assessment_id,
                    question_id=question_id,
                )
            )
            raise AppError(status_code=404, code="QUESTION_NOT_FOUND", message="Question not found")

        valid_keys = {option["key"] for option in question["options"]}
        if selected_option not in valid_keys and selected_option != "DONT_KNOW":
            logger.warning(
                build_log_message(
                    "assessment_answer_upsert_invalid_option",
                    request_id=request_id,
                    assessment_id=assessment_id,
                    question_id=question_id,
                    selected_option=selected_option,
                    allowed=sorted(valid_keys | {"DONT_KNOW"}),
                )
            )
            raise AppError(
                status_code=422,
                code="INVALID_OPTION",
                message="Invalid selected option",
                details={"allowed": sorted(valid_keys | {"DONT_KNOW"})},
            )

        updated_answers: list[dict] = []
        updated = False
        answered_at = datetime.now(UTC)
        for answer in assessment.get("answers", []):
            if answer["question_id"] == question_oid:
                updated_answers.append(
                    {
                        "question_id": question_oid,
                        "selected_option": selected_option,
                        "answered_at": answered_at,
                    }
                )
                updated = True
            else:
                updated_answers.append(answer)

        if not updated:
            updated_answers.append(
                {
                    "question_id": question_oid,
                    "selected_option": selected_option,
                    "answered_at": answered_at,
                }
            )

        await self.repository.update_assessment_answers(assessment_id=assess_oid, answers=updated_answers)
        logger.info(build_log_message(
            "assessment_answer_saved",
            request_id=request_id,
            assessment_id=assessment_id,
            question_id=question_id,
            selected_option=selected_option,
            answer_count=len(updated_answers),
        ))

    async def submit_assessment(self, *, assessment_id: str, request_id: str | None = None):
        assess_oid = _ensure_object_id(assessment_id)
        logger.info(build_log_message("assessment_submit_started", request_id=request_id, assessment_id=assessment_id))
        assessment = await self.repository.find_assessment_by_id(assessment_id=assess_oid)
        if not assessment:
            logger.warning(build_log_message("assessment_submit_not_found", request_id=request_id, assessment_id=assessment_id))
            raise AppError(status_code=404, code="ASSESSMENT_NOT_FOUND", message="Assessment not found")

        if assessment["status"] == "COMPLETED":
            logger.info(build_log_message(
                "assessment_submit_idempotent",
                request_id=request_id,
                assessment_id=assessment_id,
                completed_at=assessment["completed_at"].isoformat(),
            ))
            return {"status": "COMPLETED", "completed_at": assessment["completed_at"].isoformat()}

        required_question_ids = [
            str(item) for item in assessment.get("assigned_question_ids", [])[: settings.assessment_question_count]
        ]
        question_ids = set(required_question_ids)
        answered_ids = {str(item["question_id"]) for item in assessment.get("answers", [])}

        logger.info(build_log_message(
            "assessment_submit_attempt",
            request_id=request_id,
            assessment_id=assessment_id,
            required_question_count=len(required_question_ids),
            stored_assigned_count=len(assessment.get("assigned_question_ids", [])),
            answered_count=len(answered_ids),
        ))

        missing = sorted(question_ids - answered_ids)
        if missing:
            logger.warning(build_log_message(
                "assessment_submit_incomplete",
                request_id=request_id,
                assessment_id=assessment_id,
                missing_count=len(missing),
                missing_question_ids=missing,
            ))
            raise AppError(
                status_code=422,
                code="INCOMPLETE_ASSESSMENT",
                message="Assessment has unanswered questions",
                details={"missing_question_ids": missing},
            )

        now = datetime.now(UTC)
        question_docs = await self.repository.find_questions_by_ids(
            question_ids=assessment.get("assigned_question_ids", [])
        )
        evaluation_result = self.evaluation_engine.evaluate(
            assessment=assessment, question_docs=question_docs
        )
        result = await self.repository.complete_assessment(
            assessment_id=assess_oid,
            completed_at=now,
            evaluation_result=evaluation_result.model_dump(),
        )

        if result is None:
            latest = await self.repository.find_assessment_by_id(assessment_id=assess_oid)
            if latest and latest["status"] == "COMPLETED":
                logger.info(build_log_message(
                    "assessment_submit_raced_to_completed",
                    request_id=request_id,
                    assessment_id=assessment_id,
                    completed_at=latest["completed_at"].isoformat(),
                ))
                return {"status": "COMPLETED", "completed_at": latest["completed_at"].isoformat()}
            logger.warning(build_log_message("assessment_submit_invalid_state", request_id=request_id, assessment_id=assessment_id))
            raise AppError(status_code=409, code="INVALID_STATE", message="Unable to complete assessment")

        logger.info(build_log_message(
            "assessment_submit_completed",
            request_id=request_id,
            assessment_id=assessment_id,
            completed_at=result["completed_at"].isoformat(),
            classification_value=result.get("evaluation_result", {}).get("classification_value"),
        ))
        return {"status": "COMPLETED", "completed_at": result["completed_at"].isoformat()}
