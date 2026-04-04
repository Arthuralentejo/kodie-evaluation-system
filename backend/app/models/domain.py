from datetime import UTC, date, datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator

from app.core.utils import is_valid_cpf, normalize_cpf


class AssessmentStatus(str, Enum):
    DRAFT = "DRAFT"
    COMPLETED = "COMPLETED"


class AssessmentLevel(str, Enum):
    INICIANTE = "iniciante"
    JUNIOR = "junior"
    PLENO = "pleno"
    SENIOR = "senior"


class Option(BaseModel):
    key: str = Field(min_length=1, max_length=20)
    text: str = Field(min_length=1)

class Category(str, Enum):
    INICIANTE = "iniciante"
    JUNIOR = "junior"
    PLENO = "pleno"
    SENIOR = "senior"

class Student(BaseModel):
    cpf: str
    birth_date: date
    name: str = Field(min_length=1)
    student_id: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("cpf")
    @classmethod
    def validate_cpf(cls, value: str) -> str:
        normalized = normalize_cpf(value)
        if not is_valid_cpf(normalized):
            raise ValueError("Invalid CPF")
        return normalized


class Question(BaseModel):
    number: int = Field(ge=1)
    statement: str = Field(min_length=1)
    options: list[Option] = Field(min_length=1)
    correct_option: str
    category: Category

    @field_validator("options")
    @classmethod
    def validate_option_keys_unique(cls, value: list[Option]) -> list[Option]:
        keys = [opt.key for opt in value]
        if len(set(keys)) != len(keys):
            raise ValueError("Option keys must be unique")
        return value

    @field_validator("correct_option")
    @classmethod
    def validate_correct_option(cls, value: str) -> str:
        if value == "DONT_KNOW":
            raise ValueError("correct_option cannot be DONT_KNOW")
        return value


class AssessmentAnswer(BaseModel):
    question_id: str
    selected_option: str
    answered_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Assessment(BaseModel):
    student_id: str
    assigned_question_ids: list[str] = Field(default_factory=list)
    answers: list[AssessmentAnswer] = Field(default_factory=list)
    status: AssessmentStatus
    level: AssessmentLevel = AssessmentLevel.INICIANTE
    archived: bool = False
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None


class Answer(BaseModel):
    assessment_id: str
    question_id: str
    selected_option: str
    answered_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
