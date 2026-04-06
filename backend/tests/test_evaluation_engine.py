"""
Example-based tests for EvaluationEngine.
Covers: score_max per type, score_total, score_percent, performance_by_level,
single-level classification thresholds, geral classification.
"""
from bson import ObjectId

import pytest

from app.services.evaluation_engine import EvaluationEngine

engine = EvaluationEngine()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_question(qid, category: str, correct_option: str = "A") -> dict:
    return {"_id": qid, "category": category, "correct_option": correct_option,
            "options": [{"key": "A", "text": "a"}, {"key": "B", "text": "b"}]}


def _make_answer(qid, selected: str) -> dict:
    return {"question_id": qid, "selected_option": selected}


def _make_assessment(assessment_type: str, answers: list[dict], assigned_ids: list) -> dict:
    return {
        "assessment_type": assessment_type,
        "answers": answers,
        "assigned_question_ids": assigned_ids,
        "started_at": None,
        "completed_at": None,
    }


# ---------------------------------------------------------------------------
# score_max per assessment_type
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("assessment_type,expected_max", [
    ("iniciante", 40),
    ("junior", 60),
    ("pleno", 80),
    ("senior", 100),
    ("geral", 70),
])
def test_score_max_per_assessment_type(assessment_type, expected_max):
    result = engine.evaluate(
        assessment=_make_assessment(assessment_type, [], []),
        question_docs=[],
    )
    assert result.score_max == expected_max


# ---------------------------------------------------------------------------
# score_total: correct answers earn weight, wrong/DONT_KNOW earn 0
# ---------------------------------------------------------------------------

def test_score_total_correct_answers_earn_weight():
    q1 = ObjectId()
    q2 = ObjectId()
    q3 = ObjectId()
    q4 = ObjectId()
    questions = [
        _make_question(q1, "iniciante"),   # weight 2
        _make_question(q2, "junior"),      # weight 3
        _make_question(q3, "pleno"),       # weight 4
        _make_question(q4, "senior"),      # weight 5
    ]
    answers = [
        _make_answer(q1, "A"),  # correct → +2
        _make_answer(q2, "A"),  # correct → +3
        _make_answer(q3, "A"),  # correct → +4
        _make_answer(q4, "A"),  # correct → +5
    ]
    assessment = _make_assessment("geral", answers, [q1, q2, q3, q4])
    result = engine.evaluate(assessment=assessment, question_docs=questions)
    assert result.score_total == 14  # 2+3+4+5


def test_score_total_wrong_answers_earn_zero():
    q1 = ObjectId()
    questions = [_make_question(q1, "senior")]  # weight 5
    answers = [_make_answer(q1, "B")]  # wrong
    assessment = _make_assessment("senior", answers, [q1])
    result = engine.evaluate(assessment=assessment, question_docs=questions)
    assert result.score_total == 0
    assert result.incorrect_count == 1


def test_score_total_dont_know_earns_zero():
    q1 = ObjectId()
    questions = [_make_question(q1, "pleno")]  # weight 4
    answers = [_make_answer(q1, "DONT_KNOW")]
    assessment = _make_assessment("pleno", answers, [q1])
    result = engine.evaluate(assessment=assessment, question_docs=questions)
    assert result.score_total == 0
    assert result.dont_know_count == 1
    assert result.incorrect_count == 0


def test_score_total_mixed_answers():
    q1 = ObjectId()
    q2 = ObjectId()
    q3 = ObjectId()
    questions = [
        _make_question(q1, "junior"),   # weight 3
        _make_question(q2, "junior"),   # weight 3
        _make_question(q3, "junior"),   # weight 3
    ]
    answers = [
        _make_answer(q1, "A"),          # correct → +3
        _make_answer(q2, "B"),          # wrong → 0
        _make_answer(q3, "DONT_KNOW"),  # dont_know → 0
    ]
    assessment = _make_assessment("junior", answers, [q1, q2, q3])
    result = engine.evaluate(assessment=assessment, question_docs=questions)
    assert result.score_total == 3
    assert result.correct_count == 1
    assert result.incorrect_count == 1
    assert result.dont_know_count == 1


# ---------------------------------------------------------------------------
# score_percent formula
# ---------------------------------------------------------------------------

def test_score_percent_formula():
    # 2 correct iniciante questions → score_total=4, score_max=40 → 10.0%
    q1 = ObjectId()
    q2 = ObjectId()
    questions = [_make_question(q1, "iniciante"), _make_question(q2, "iniciante")]
    answers = [_make_answer(q1, "A"), _make_answer(q2, "A")]
    assessment = _make_assessment("iniciante", answers, [q1, q2])
    result = engine.evaluate(assessment=assessment, question_docs=questions)
    assert result.score_percent == round((4 / 40) * 100, 2)


def test_score_percent_zero_when_no_correct():
    assessment = _make_assessment("junior", [], [])
    result = engine.evaluate(assessment=assessment, question_docs=[])
    assert result.score_percent == 0.0


# ---------------------------------------------------------------------------
# performance_by_level: all 4 canonical keys, accuracy=null when total=0
# ---------------------------------------------------------------------------

def test_performance_by_level_has_all_four_canonical_keys():
    assessment = _make_assessment("iniciante", [], [])
    result = engine.evaluate(assessment=assessment, question_docs=[])
    assert set(result.performance_by_level.keys()) == {"iniciante", "junior", "pleno", "senior"}


def test_performance_by_level_accuracy_null_when_total_zero():
    assessment = _make_assessment("iniciante", [], [])
    result = engine.evaluate(assessment=assessment, question_docs=[])
    for lvl in ("iniciante", "junior", "pleno", "senior"):
        perf = result.performance_by_level[lvl]
        assert perf.total == 0
        assert perf.accuracy is None


def test_performance_by_level_accuracy_computed_when_total_nonzero():
    q1 = ObjectId()
    q2 = ObjectId()
    questions = [_make_question(q1, "junior"), _make_question(q2, "junior")]
    answers = [_make_answer(q1, "A"), _make_answer(q2, "B")]  # 1 correct, 1 wrong
    assessment = _make_assessment("junior", answers, [q1, q2])
    result = engine.evaluate(assessment=assessment, question_docs=questions)
    perf = result.performance_by_level["junior"]
    assert perf.total == 2
    assert perf.correct == 1
    assert perf.accuracy == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# Single-level classification thresholds
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("assessment_type", ["iniciante", "junior", "pleno", "senior"])
def test_single_level_classification_kind_is_level_fit(assessment_type):
    assessment = _make_assessment(assessment_type, [], [])
    result = engine.evaluate(assessment=assessment, question_docs=[])
    assert result.classification_kind == "level_fit"


def test_single_level_below_expected_when_score_percent_below_50():
    # 0 correct → score_percent = 0 → below_expected
    assessment = _make_assessment("iniciante", [], [])
    result = engine.evaluate(assessment=assessment, question_docs=[])
    assert result.classification_value == "below_expected"


def test_single_level_at_level_when_score_percent_exactly_50():
    # Need score_percent == 50 for iniciante: score_max=40, need score_total=20
    # 10 correct iniciante questions (weight 2 each) = 20 points
    qids = [ObjectId() for _ in range(10)]
    questions = [_make_question(qid, "iniciante") for qid in qids]
    answers = [_make_answer(qid, "A") for qid in qids]
    assessment = _make_assessment("iniciante", answers, qids)
    result = engine.evaluate(assessment=assessment, question_docs=questions)
    assert result.score_percent == 50.0
    assert result.classification_value == "at_level"


def test_single_level_at_level_when_score_percent_exactly_70():
    # score_percent == 70 for junior: score_max=60, need score_total=42
    # 14 correct junior questions (weight 3 each) = 42 points
    qids = [ObjectId() for _ in range(14)]
    questions = [_make_question(qid, "junior") for qid in qids]
    answers = [_make_answer(qid, "A") for qid in qids]
    assessment = _make_assessment("junior", answers, qids)
    result = engine.evaluate(assessment=assessment, question_docs=questions)
    assert result.score_percent == 70.0
    assert result.classification_value == "at_level"


def test_single_level_above_expected_when_score_percent_above_70():
    # All 20 senior questions correct: score_total=100, score_max=100 → 100%
    qids = [ObjectId() for _ in range(20)]
    questions = [_make_question(qid, "senior") for qid in qids]
    answers = [_make_answer(qid, "A") for qid in qids]
    assessment = _make_assessment("senior", answers, qids)
    result = engine.evaluate(assessment=assessment, question_docs=questions)
    assert result.score_percent == 100.0
    assert result.classification_value == "above_expected"


# ---------------------------------------------------------------------------
# Geral classification
# ---------------------------------------------------------------------------

def test_geral_classification_kind_is_consistency_level():
    assessment = _make_assessment("geral", [], [])
    result = engine.evaluate(assessment=assessment, question_docs=[])
    assert result.classification_kind == "consistency_level"


def test_geral_defaults_to_iniciante_when_no_level_qualifies():
    # All answers wrong → no level reaches 0.70 accuracy
    qids = [ObjectId() for _ in range(4)]
    questions = [
        _make_question(qids[0], "iniciante"),
        _make_question(qids[1], "junior"),
        _make_question(qids[2], "pleno"),
        _make_question(qids[3], "senior"),
    ]
    answers = [_make_answer(qid, "B") for qid in qids]  # all wrong
    assessment = _make_assessment("geral", answers, qids)
    result = engine.evaluate(assessment=assessment, question_docs=questions)
    assert result.classification_value == "iniciante"


def test_geral_classifies_by_highest_qualifying_level():
    # 5 questions per level, all correct → accuracy=1.0 for all → highest = senior
    qids_by_level = {
        "iniciante": [ObjectId() for _ in range(5)],
        "junior":    [ObjectId() for _ in range(5)],
        "pleno":     [ObjectId() for _ in range(5)],
        "senior":    [ObjectId() for _ in range(5)],
    }
    questions = []
    answers = []
    assigned_ids = []
    for level, qids in qids_by_level.items():
        for qid in qids:
            questions.append(_make_question(qid, level))
            answers.append(_make_answer(qid, "A"))
            assigned_ids.append(qid)

    assessment = _make_assessment("geral", answers, assigned_ids)
    result = engine.evaluate(assessment=assessment, question_docs=questions)
    assert result.classification_value == "senior"


def test_geral_classifies_as_junior_when_only_iniciante_and_junior_qualify():
    # iniciante: 5/5 correct (1.0), junior: 4/5 correct (0.8), pleno: 2/5 (0.4), senior: 0/5 (0.0)
    qids_by_level = {
        "iniciante": [ObjectId() for _ in range(5)],
        "junior":    [ObjectId() for _ in range(5)],
        "pleno":     [ObjectId() for _ in range(5)],
        "senior":    [ObjectId() for _ in range(5)],
    }
    questions = []
    answers = []
    assigned_ids = []
    correct_counts = {"iniciante": 5, "junior": 4, "pleno": 2, "senior": 0}
    for level, qids in qids_by_level.items():
        for i, qid in enumerate(qids):
            questions.append(_make_question(qid, level))
            assigned_ids.append(qid)
            if i < correct_counts[level]:
                answers.append(_make_answer(qid, "A"))  # correct
            else:
                answers.append(_make_answer(qid, "B"))  # wrong

    assessment = _make_assessment("geral", answers, assigned_ids)
    result = engine.evaluate(assessment=assessment, question_docs=questions)
    assert result.classification_value == "junior"


def test_geral_accuracy_threshold_boundary_exactly_070():
    # junior: 7/10 correct = 0.70 → qualifies; pleno: 6/10 = 0.60 → does not
    qids_junior = [ObjectId() for _ in range(10)]
    qids_pleno  = [ObjectId() for _ in range(10)]
    questions = (
        [_make_question(qid, "junior") for qid in qids_junior] +
        [_make_question(qid, "pleno")  for qid in qids_pleno]
    )
    answers = (
        [_make_answer(qid, "A") for qid in qids_junior[:7]] +
        [_make_answer(qid, "B") for qid in qids_junior[7:]] +
        [_make_answer(qid, "A") for qid in qids_pleno[:6]] +
        [_make_answer(qid, "B") for qid in qids_pleno[6:]]
    )
    assigned_ids = qids_junior + qids_pleno
    assessment = _make_assessment("geral", answers, assigned_ids)
    result = engine.evaluate(assessment=assessment, question_docs=questions)
    assert result.classification_value == "junior"
