from datetime import date

from pydantic import BaseModel, Field, field_validator

from app.core.utils import is_valid_cpf, normalize_cpf
from app.models.domain import AssessmentType


class AuthRequest(BaseModel):
    cpf: str
    birth_date: date

    @field_validator("cpf")
    @classmethod
    def validate_cpf(cls, value: str) -> str:
        normalized = normalize_cpf(value)
        if not is_valid_cpf(normalized):
            raise ValueError("Invalid CPF")
        return normalized


class AuthResponse(BaseModel):
    token: str


class RevokeResponse(BaseModel):
    status: str


class CompletedAssessmentSummary(BaseModel):
    assessment_id: str
    assessment_type: str
    completed_at: str


class AssessmentSummaryResponse(BaseModel):
    status: str
    assessment_id: str | None = None
    completed_at: str | None = None
    assessment_type: str | None = None
    assessments: list[CompletedAssessmentSummary] = []


class CreateAssessmentRequest(BaseModel):
    assessment_type: AssessmentType = Field(
        description="The desired assessment type",
    )


class CreateAssessmentResponse(BaseModel):
    assessment_id: str
    status: str
    assessment_type: str


class QuestionOptionResponse(BaseModel):
    key: str
    text: str


class QuestionResponse(BaseModel):
    id: str
    statement: str
    options: list[QuestionOptionResponse]
    selected_option: str | None = None


class UpsertAnswerRequest(BaseModel):
    question_id: str = Field(min_length=1)
    selected_option: str = Field(min_length=1)


class SubmitResponse(BaseModel):
    status: str
    completed_at: str


# --- Admin / evaluation response models ---


class LevelPerformanceResponse(BaseModel):
    correct: int
    total: int
    accuracy: float | None


class EvaluationResultResponse(BaseModel):
    assessment_type: str
    score_total: int
    score_max: int
    score_percent: float
    performance_by_level: dict[str, LevelPerformanceResponse]
    classification_kind: str
    classification_value: str
    duration_seconds: int
    correct_count: int
    incorrect_count: int
    dont_know_count: int
    evaluated_at: str


class QuestionResultResponse(BaseModel):
    question_id: str
    category: str
    selected_option: str
    correct_option: str
    is_correct: bool
    points_earned: int


class AdminResultSummary(BaseModel):
    assessment_id: str
    student_id: str
    assessment_type: str
    score_total: int | None = None
    score_max: int | None = None
    score_percent: float | None = None
    performance_by_level: dict[str, LevelPerformanceResponse] | None = None
    classification_kind: str | None = None
    classification_value: str | None = None
    duration_seconds: int | None = None
    completed_at: str
    evaluation_result: EvaluationResultResponse | None = None


class AdminResultDetail(AdminResultSummary):
    question_results: list[QuestionResultResponse] | None = None


class RankingEntry(BaseModel):
    rank: int
    assessment_id: str
    student_id: str
    assessment_type: str | None = None
    score_total: int
    score_max: int
    score_percent: float
    classification_value: str | None = None
    duration_seconds: int
    completed_at: str


class RankingPage(BaseModel):
    entries: list[RankingEntry]
    total: int
    page: int
    page_size: int


class ScoreDistributionBucket(BaseModel):
    bucket: str
    count: int


class LevelAccuracyStat(BaseModel):
    level: str
    mean_accuracy: float | None


class AnalyticsResult(BaseModel):
    score_distribution_raw: list[ScoreDistributionBucket]
    score_distribution_normalized: list[ScoreDistributionBucket]
    classification_distribution: dict[str, int]
    level_accuracy: list[LevelAccuracyStat]
    assessment_type_filter: str | None
