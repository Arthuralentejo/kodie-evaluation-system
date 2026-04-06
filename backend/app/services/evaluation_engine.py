from datetime import UTC, datetime

from app.core.errors import AppError
from app.core.logger import build_log_message, get_logger
from app.models.domain import EvaluationResult, LevelPerformance, QuestionResult

logger = get_logger("kodie.services.evaluation")


class EvaluationEngine:
    WEIGHTS: dict[str, int] = {"iniciante": 2, "junior": 3, "pleno": 4, "senior": 5}
    SCORE_MAX: dict[str, int] = {
        "iniciante": 40,
        "junior": 60,
        "pleno": 80,
        "senior": 100,
        "geral": 70,
    }
    CANONICAL_LEVELS: tuple[str, ...] = ("iniciante", "junior", "pleno", "senior")
    ACCURACY_THRESHOLD: float = 0.70

    def evaluate(
        self, *, assessment: dict, question_docs: list[dict]
    ) -> EvaluationResult:
        """Compute full evaluation result from assessment doc and question docs."""
        assessment_type = assessment.get("assessment_type", "iniciante")
        score_max = self.SCORE_MAX.get(assessment_type)
        if score_max is None:
            raise AppError(
                status_code=422,
                code="INVALID_ASSESSMENT_TYPE",
                message="Unknown assessment type",
            )

        question_by_id = {q["_id"]: q for q in question_docs}
        answers = assessment.get("answers", [])
        assigned_ids = assessment.get("assigned_question_ids", [])

        score_total, correct_count, incorrect_count, dont_know_count = (
            self._compute_score(answers, question_by_id)
        )
        score_percent = (
            round((score_total / score_max) * 100, 2) if score_max > 0 else 0.0
        )
        performance_by_level = self._compute_performance_by_level(
            answers, question_by_id, assigned_ids
        )
        classification_kind, classification_value = self._classify(
            assessment_type, score_percent, performance_by_level
        )

        started_at = assessment.get("started_at")
        completed_at = assessment.get("completed_at") or datetime.now(UTC)
        duration_seconds = (
            int((completed_at - started_at).total_seconds()) if started_at else 0
        )

        question_results = self._compute_question_results(answers, question_by_id)

        result = EvaluationResult(
            assessment_type=assessment_type,
            score_total=score_total,
            score_max=score_max,
            score_percent=score_percent,
            performance_by_level=performance_by_level,
            classification_kind=classification_kind,
            classification_value=classification_value,
            duration_seconds=duration_seconds,
            correct_count=correct_count,
            incorrect_count=incorrect_count,
            dont_know_count=dont_know_count,
            evaluated_at=datetime.now(UTC),
            question_results=question_results,
        )
        logger.info(
            build_log_message(
                "evaluation_completed",
                assessment_id=str(assessment.get("_id"))
                if assessment.get("_id") is not None
                else None,
                assessment_type=assessment_type,
                answer_count=len(answers),
                question_count=len(question_docs),
                score_total=score_total,
                score_percent=score_percent,
                classification_kind=classification_kind,
                classification_value=classification_value,
                duration_seconds=duration_seconds,
            )
        )
        return result

    def _compute_score(
        self, answers: list[dict], question_by_id: dict
    ) -> tuple[int, int, int, int]:
        score_total = 0
        correct_count = 0
        incorrect_count = 0
        dont_know_count = 0
        for answer in answers:
            selected = answer.get("selected_option")
            if selected == "DONT_KNOW":
                dont_know_count += 1
                continue
            q = question_by_id.get(answer.get("question_id"))
            if q is None:
                continue
            category = q.get("category", "")
            weight = self.WEIGHTS.get(category, 0)
            if selected == q.get("correct_option"):
                score_total += weight
                correct_count += 1
            else:
                incorrect_count += 1
        return score_total, correct_count, incorrect_count, dont_know_count

    def _compute_performance_by_level(
        self, answers: list[dict], question_by_id: dict, assigned_ids: list
    ) -> dict[str, LevelPerformance]:
        totals: dict[str, int] = {lvl: 0 for lvl in self.CANONICAL_LEVELS}
        corrects: dict[str, int] = {lvl: 0 for lvl in self.CANONICAL_LEVELS}

        for qid in assigned_ids:
            q = question_by_id.get(qid)
            if q is None:
                continue
            cat = q.get("category", "")
            if cat in totals:
                totals[cat] += 1

        for answer in answers:
            selected = answer.get("selected_option")
            q = question_by_id.get(answer.get("question_id"))
            if q is None:
                continue
            cat = q.get("category", "")
            if cat in corrects and selected == q.get("correct_option"):
                corrects[cat] += 1

        result = {}
        for lvl in self.CANONICAL_LEVELS:
            total = totals[lvl]
            correct = corrects[lvl]
            accuracy = (correct / total) if total > 0 else None
            result[lvl] = LevelPerformance(
                correct=correct, total=total, accuracy=accuracy
            )
        return result

    def _classify(
        self,
        assessment_type: str,
        score_percent: float,
        performance_by_level: dict[str, LevelPerformance],
    ) -> tuple[str, str]:
        if assessment_type == "geral":
            classification_kind = "consistency_level"
            classification_value = "iniciante"
            for lvl in self.CANONICAL_LEVELS:
                perf = performance_by_level.get(lvl)
                if (
                    perf
                    and perf.accuracy is not None
                    and perf.accuracy >= self.ACCURACY_THRESHOLD
                ):
                    classification_value = lvl
            return classification_kind, classification_value
        else:
            classification_kind = "level_fit"
            if score_percent < 50:
                classification_value = "below_expected"
            elif score_percent <= 70:
                classification_value = "at_level"
            else:
                classification_value = "above_expected"
            return classification_kind, classification_value

    def _compute_question_results(
        self, answers: list[dict], question_by_id: dict
    ) -> list[QuestionResult]:
        results = []
        for answer in answers:
            q = question_by_id.get(answer.get("question_id"))
            if q is None:
                continue
            selected = answer.get("selected_option", "")
            correct = q.get("correct_option", "")
            category = q.get("category", "")
            is_correct = selected == correct
            points_earned = self.WEIGHTS.get(category, 0) if is_correct else 0
            results.append(
                QuestionResult(
                    question_id=str(answer.get("question_id")),
                    category=category,
                    selected_option=selected,
                    correct_option=correct,
                    is_correct=is_correct,
                    points_earned=points_earned,
                )
            )
        return results
