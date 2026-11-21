from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ExperienceRecord(BaseModel):
    """Единый источник истины (SSOT) по конкретному этапу опыта или проекту."""

    record_id: str = Field(min_length=1, max_length=64)
    company: str = Field(min_length=1, max_length=128)
    role: str = Field(min_length=1, max_length=128)
    start_year: int = Field(ge=1980, le=2030)
    end_year: int = Field(ge=1980, le=2030)
    skills: list[str] = Field(min_length=1)
    summary: str = Field(min_length=1)


class ResumeClaim(BaseModel):
    """Фактологическое утверждение в сгенерированном резюме/ответе, подлежащее Z3-проверке."""

    source_record_id: str = Field(min_length=1, max_length=64)
    company: str = Field(min_length=1, max_length=128)
    start_year: int = Field(ge=1980, le=2030)
    end_year: int = Field(ge=1980, le=2030)
    claimed_skills: list[str] = Field(default_factory=list)
    bullet_text: str = Field(min_length=1, max_length=600)


class TailoredAnswerProposal(BaseModel):
    """Структурированный ответ LLM под конкретную вакансию."""

    target_role: str = Field(min_length=1, max_length=128)
    claims: list[ResumeClaim] = Field(min_length=1, max_length=12)
    missing_required_skills: list[str] = Field(default_factory=list)


class FactAuditVerdict(BaseModel):
    """Вердикт Z3 Fact-Checker: доказательство отсутствия галлюцинаций."""

    status: Literal["SAT", "UNSAT"]
    verified_claims: int
    violations: list[str] = Field(default_factory=list)
