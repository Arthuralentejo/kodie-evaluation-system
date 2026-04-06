from pymongo import ASCENDING, DESCENDING

from app.core.logger import build_log_message, get_logger
from app.db.collections import (
    assessments_collection,
    denylist_collection,
    questions_collection,
    students_collection,
)
from app.db.mongo import get_db

logger = get_logger("kodie.db.indexes")


async def ensure_indexes() -> None:
    db = get_db()
    logger.info(
        build_log_message("mongo_indexes_ensure_started", mongo_db_name=db.name)
    )

    await students_collection(db).create_index(
        [("cpf", ASCENDING)], unique=True, name="uq_students_cpf"
    )

    await students_collection(db).create_index(
        [("student_id", ASCENDING)], unique=True, name="uq_students_student_id"
    )

    await assessments_collection(db).create_index(
        [("student_id", ASCENDING)],
        unique=True,
        partialFilterExpression={"archived": False},
        name="uq_assessment_active_student",
    )

    # Completed history lookups
    await assessments_collection(db).create_index(
        [
            ("student_id", ASCENDING),
            ("status", ASCENDING),
            ("completed_at", DESCENDING),
        ],
        name="idx_assessment_student_status_completed_at",
    )

    await questions_collection(db).create_index(
        [("number", ASCENDING)],
        unique=True,
        name="uq_question_number",
    )

    await denylist_collection(db).create_index(
        [("expires_at", ASCENDING)],
        expireAfterSeconds=0,
        name="ttl_denylist_expires_at",
    )

    # Evaluation result indexes
    await assessments_collection(db).create_index(
        [("assessment_type", ASCENDING), ("status", ASCENDING)],
        name="idx_assessment_type_status",
    )

    await assessments_collection(db).create_index(
        [("evaluation_result.classification_value", ASCENDING), ("status", ASCENDING)],
        name="idx_evaluation_classification_value_status",
    )

    await assessments_collection(db).create_index(
        [("evaluation_result.score_total", DESCENDING), ("status", ASCENDING)],
        name="idx_evaluation_score_total_status",
    )

    await assessments_collection(db).create_index(
        [("evaluation_result.score_percent", DESCENDING), ("status", ASCENDING)],
        name="idx_evaluation_score_percent_status",
    )
    logger.info(
        build_log_message("mongo_indexes_ensure_completed", mongo_db_name=db.name)
    )
