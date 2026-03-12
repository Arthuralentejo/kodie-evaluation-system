from pymongo import ASCENDING

from app.db.collections import answers_collection, assessments_collection, denylist_collection, students_collection
from app.db.mongo import get_db


async def ensure_indexes() -> None:
    db = get_db()

    await students_collection(db).create_index([("cpf", ASCENDING)], unique=True, name="uq_students_cpf")

    await assessments_collection(db).create_index(
        [("student_id", ASCENDING), ("status", ASCENDING)],
        unique=True,
        partialFilterExpression={"status": "DRAFT"},
        name="uq_assessment_student_draft",
    )

    await answers_collection(db).create_index(
        [("assessment_id", ASCENDING), ("question_id", ASCENDING)],
        unique=True,
        name="uq_answer_assessment_question",
    )

    await denylist_collection(db).create_index(
        [("expires_at", ASCENDING)],
        expireAfterSeconds=0,
        name="ttl_denylist_expires_at",
    )
