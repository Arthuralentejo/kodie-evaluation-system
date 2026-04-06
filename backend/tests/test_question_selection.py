from bson import ObjectId
import pytest

from app.core.errors import AppError
from app.models.domain import AssessmentType
from app.services.question_selection import build_assigned_question_ids, build_geral_question_ids


def make_docs(categories: list[str]) -> list[dict]:
    return [
        {"_id": ObjectId(), "number": i + 1, "category": cat}
        for i, cat in enumerate(categories)
    ]


def test_build_assigned_question_ids_caps_assessment_size():
    # Pre-filtered pool of 32 questions (all same level, simulating DB-level filter)
    docs = make_docs(["senior"] * 32)

    assigned_ids = build_assigned_question_ids(docs, level=AssessmentType.SENIOR)

    assert len(assigned_ids) == 20


def test_build_assigned_question_ids_returns_all_when_below_cap():
    # Pre-filtered pool of 5 questions — all returned (below the 20-question cap)
    docs = make_docs(["iniciante"] * 5)

    assigned_ids = build_assigned_question_ids(docs, level=AssessmentType.INICIANTE)

    assert len(assigned_ids) == 5


def test_build_assigned_question_ids_uses_pre_filtered_docs():
    # DB already filtered to only junior questions — no in-Python filtering
    docs = make_docs(["junior"] * 10)

    assigned_ids = build_assigned_question_ids(docs, level=AssessmentType.JUNIOR)

    assert len(assigned_ids) == 10


def test_build_assigned_question_ids_default_level_is_iniciante():
    # No level argument — default is INICIANTE; docs are pre-filtered by caller
    docs = make_docs(["iniciante"] * 3)

    assigned_ids = build_assigned_question_ids(docs)

    assert len(assigned_ids) == 3


def test_build_assigned_question_ids_empty_pool_returns_empty():
    assigned_ids = build_assigned_question_ids([])

    assert assigned_ids == []


# --- build_geral_question_ids tests ---

def _make_geral_pool(per_level: int = 5) -> list[dict]:
    """Create a pool with exactly `per_level` questions per canonical level."""
    levels = ["iniciante", "junior", "pleno", "senior"]
    docs = []
    num = 1
    for lvl in levels:
        for _ in range(per_level):
            docs.append({"_id": ObjectId(), "number": num, "category": lvl})
            num += 1
    return docs


def test_build_geral_question_ids_returns_exactly_20():
    docs = _make_geral_pool(per_level=10)
    ids = build_geral_question_ids(docs)
    assert len(ids) == 20


def test_build_geral_question_ids_exactly_5_per_level():
    from app.models.domain import Category
    from app.services.question_selection import normalize_category

    docs = _make_geral_pool(per_level=10)
    # attach category back for verification
    id_to_cat = {d["_id"]: d["category"] for d in docs}
    ids = build_geral_question_ids(docs)

    counts: dict[str, int] = {}
    for oid in ids:
        cat = id_to_cat[oid]
        counts[cat] = counts.get(cat, 0) + 1

    assert counts == {"iniciante": 5, "junior": 5, "pleno": 5, "senior": 5}


def test_build_geral_question_ids_raises_when_level_has_fewer_than_5():
    # Only 4 pleno questions — should raise
    levels = ["iniciante"] * 10 + ["junior"] * 10 + ["pleno"] * 4 + ["senior"] * 10
    docs = [{"_id": ObjectId(), "number": i + 1, "category": lvl} for i, lvl in enumerate(levels)]

    with pytest.raises(AppError) as exc:
        build_geral_question_ids(docs)

    assert exc.value.status_code == 409
    assert exc.value.code == "NO_QUESTIONS_FOR_LEVEL"


def test_build_geral_question_ids_is_deterministic():
    docs = _make_geral_pool(per_level=10)
    ids_first = build_geral_question_ids(docs)
    ids_second = build_geral_question_ids(docs)
    assert ids_first == ids_second
