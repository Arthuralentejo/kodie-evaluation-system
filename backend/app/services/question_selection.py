from bson import ObjectId

from app.core.config import settings
from app.core.errors import AppError
from app.models.domain import AssessmentType, Category


CATEGORY_ORDER = (
    Category.INICIANTE,
    Category.JUNIOR,
    Category.PLENO,
    Category.SENIOR,
)


def normalize_category(category: str | Category) -> Category | None:
    if isinstance(category, Category):
        return category

    normalized = category.strip().lower()
    try:
        return Category(normalized)
    except ValueError:
        return None


def select_questions_by_difficulty(question_docs: list[dict], quantity: int | None) -> list[dict]:
    ordered_questions = sorted(question_docs, key=lambda item: item.get("number", 0))
    if quantity is None or quantity >= len(ordered_questions):
        return ordered_questions

    buckets: dict[Category, list[dict]] = {category: [] for category in CATEGORY_ORDER}
    extra_questions: list[dict] = []
    for question in ordered_questions:
        normalized_category = normalize_category(question.get("category", ""))
        if normalized_category in buckets:
            buckets[normalized_category].append(question)
        else:
            extra_questions.append(question)

    if extra_questions:
        buckets[CATEGORY_ORDER[0]].extend(extra_questions)

    weights = {
        Category.INICIANTE: 4,
        Category.JUNIOR: 3,
        Category.PLENO: 2,
        Category.SENIOR: 1,
    }
    total_weight = sum(weights.values())
    counts = {
        category: min(len(buckets[category]), (quantity * weights[category]) // total_weight)
        for category in CATEGORY_ORDER
    }

    remaining = quantity - sum(counts.values())
    while remaining > 0:
        allocated = False
        for category in CATEGORY_ORDER:
            if counts[category] < len(buckets[category]):
                counts[category] += 1
                remaining -= 1
                allocated = True
                if remaining == 0:
                    break
        if not allocated:
            break

    selected: list[dict] = []
    for category in CATEGORY_ORDER:
        selected.extend(buckets[category][: counts[category]])
    return selected


def build_assigned_question_ids(
    question_docs: list[dict],
    level: AssessmentType = AssessmentType.INICIANTE,
) -> list[ObjectId]:
    # question_docs already pre-filtered by category=level at DB level
    selected_questions = select_questions_by_difficulty(question_docs, settings.assessment_question_count)
    return [question["_id"] for question in selected_questions]


def build_geral_question_ids(question_docs: list[dict]) -> list[ObjectId]:
    """Selects exactly 5 questions per canonical level (20 total).
    Raises NO_QUESTIONS_FOR_LEVEL if any level has fewer than 5 questions."""
    PER_LEVEL = 5

    buckets: dict[Category, list[dict]] = {cat: [] for cat in CATEGORY_ORDER}
    for q in question_docs:
        cat = normalize_category(q.get("category", ""))
        if cat in buckets:
            buckets[cat].append(q)

    for cat in CATEGORY_ORDER:
        if len(buckets[cat]) < PER_LEVEL:
            raise AppError(
                status_code=409,
                code="NO_QUESTIONS_FOR_LEVEL",
                message=f"Não há questões suficientes para o nível {cat.value}.",
            )

    selected: list[dict] = []
    for cat in CATEGORY_ORDER:
        bucket = sorted(buckets[cat], key=lambda q: q.get("number", 0))
        selected.extend(bucket[:PER_LEVEL])

    return [q["_id"] for q in selected]
