from bson import ObjectId

from app.models.domain import AssessmentLevel
from app.services.question_selection import build_assigned_question_ids


def make_docs(categories: list[str]) -> list[dict]:
    return [
        {"_id": ObjectId(), "number": i + 1, "category": cat}
        for i, cat in enumerate(categories)
    ]


def test_build_assigned_question_ids_caps_assessment_size():
    # Pre-filtered pool of 32 questions (all same level, simulating DB-level filter)
    docs = make_docs(["senior"] * 32)

    assigned_ids = build_assigned_question_ids(docs, level=AssessmentLevel.SENIOR)

    assert len(assigned_ids) == 20


def test_build_assigned_question_ids_returns_all_when_below_cap():
    # Pre-filtered pool of 5 questions — all returned (below the 20-question cap)
    docs = make_docs(["iniciante"] * 5)

    assigned_ids = build_assigned_question_ids(docs, level=AssessmentLevel.INICIANTE)

    assert len(assigned_ids) == 5


def test_build_assigned_question_ids_uses_pre_filtered_docs():
    # DB already filtered to only junior questions — no in-Python filtering
    docs = make_docs(["junior"] * 10)

    assigned_ids = build_assigned_question_ids(docs, level=AssessmentLevel.JUNIOR)

    assert len(assigned_ids) == 10


def test_build_assigned_question_ids_default_level_is_iniciante():
    # No level argument — default is INICIANTE; docs are pre-filtered by caller
    docs = make_docs(["iniciante"] * 3)

    assigned_ids = build_assigned_question_ids(docs)

    assert len(assigned_ids) == 3


def test_build_assigned_question_ids_empty_pool_returns_empty():
    assigned_ids = build_assigned_question_ids([])

    assert assigned_ids == []
