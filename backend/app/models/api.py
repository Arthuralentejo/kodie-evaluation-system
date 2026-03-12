from datetime import date

from pydantic import BaseModel, Field, field_validator

from app.core.utils import is_valid_cpf, normalize_cpf


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
    assessment_id: str


class RevokeResponse(BaseModel):
    status: str


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
