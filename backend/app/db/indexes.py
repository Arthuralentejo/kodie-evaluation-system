from pymongo import ASCENDING, DESCENDING

from app.db.collections import (
    assessments_collection,
    denylist_collection,
    questions_collection,
    students_collection,
)
from app.db.mongo import get_db


async def ensure_indexes() -> None:
    db = get_db()

    await students_collection(db).create_index([("cpf", ASCENDING)], unique=True, name="uq_students_cpf")

    await students_collection(db).create_index([("student_id", ASCENDING)], unique=True, name="uq_students_student_id")

    await assessments_collection(db).create_index(
        [("student_id", ASCENDING)],
        unique=True,
        partialFilterExpression={"archived": False},
        name="uq_assessment_active_student",
    )

    # Completed history lookups
    await assessments_collection(db).create_index(
        [("student_id", ASCENDING), ("status", ASCENDING), ("completed_at", DESCENDING)],
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
