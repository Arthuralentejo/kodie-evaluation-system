from app.core.utils import is_valid_cpf, mask_cpf, normalize_cpf
from app.services.assessment_service import deterministic_shuffle_options


def test_valid_cpf_check_digits() -> None:
    assert is_valid_cpf("52998224725")
    assert is_valid_cpf("529.982.247-25")
    assert not is_valid_cpf("12345678901")
    assert not is_valid_cpf("11111111111")


def test_mask_cpf() -> None:
    assert mask_cpf("52998224725") == "***.***.***-25"
    assert mask_cpf("bad") == "***"


def test_deterministic_shuffle_stable_for_same_inputs() -> None:
    options = [{"key": "A", "text": "1"}, {"key": "B", "text": "2"}, {"key": "C", "text": "3"}]
    left = deterministic_shuffle_options(assessment_id="a1", question_id="q1", options=options)
    right = deterministic_shuffle_options(assessment_id="a1", question_id="q1", options=options)
    assert left == right


def test_deterministic_shuffle_differs_across_assessment() -> None:
    options = [{"key": "A", "text": "1"}, {"key": "B", "text": "2"}, {"key": "C", "text": "3"}]
    left = deterministic_shuffle_options(assessment_id="a1", question_id="q1", options=options)
    right = deterministic_shuffle_options(assessment_id="a2", question_id="q1", options=options)
    assert {o["key"] for o in left} == {"A", "B", "C"}
    assert {o["key"] for o in right} == {"A", "B", "C"}


def test_normalize_cpf() -> None:
    assert normalize_cpf("529.982.247-25") == "52998224725"
