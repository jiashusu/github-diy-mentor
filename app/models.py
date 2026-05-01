from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl


class RepoFiles(BaseModel):
    readme: str = ""
    package_json: str = ""
    requirements_txt: str = ""


class RepoCandidate(BaseModel):
    name: str
    url: HttpUrl
    description: str | None = None
    description_en: str | None = None
    description_zh: str | None = None
    homepage_url: HttpUrl | None = None
    language: str | None = None
    topics: list[str] = Field(default_factory=list)
    stars_total: int = 0
    stars_last_7d_estimate: int = 0
    forks: int = 0
    pushed_at: str | None = None
    has_visual_signal: bool = False
    trend_score: float = 0
    files: RepoFiles = Field(default_factory=RepoFiles)


class AnalyzeRequest(BaseModel):
    repo: RepoCandidate


class AnalysisResult(BaseModel):
    language: Literal["zh", "en"] = "zh"
    plain_summary: str
    difficulty_score: int = Field(ge=1, le=10)
    macos_requirements: list[str]
    windows_requirements: list[str]
    likely_run_commands: list[str]
    notes: list[str] = Field(default_factory=list)


class MentorIdea(BaseModel):
    type: Literal["懒人方案", "AI增强版", "Lazy Plan", "AI Upgrade"]
    title: str
    direction: str
    for_whom: str
    minimum_steps: list[str]
    ai_capability: str
    files_or_modules_to_check: list[str]
    difficulty: Literal["低", "中", "高", "Low", "Medium", "High"]
    why_this_is_useful: str


class Pitfall(BaseModel):
    platform: Literal["macOS", "Windows", "通用", "General"]
    symptom: str
    likely_cause: str
    fix: str


class MentorResult(BaseModel):
    overall_angle: str
    ideas: list[MentorIdea]
    pitfalls: list[Pitfall]


class MentorRequest(BaseModel):
    repo: RepoCandidate
    analysis: AnalysisResult | None = None


class FullAnalysisRequest(BaseModel):
    repo: RepoCandidate
    ui_language: Literal["zh", "en"] = "zh"


class FullAnalysisResult(BaseModel):
    repo: RepoCandidate
    analysis: AnalysisResult
    mentor: MentorResult
    cached: bool = False


class ErrorMessage(BaseModel):
    detail: str
    extra: dict[str, Any] = Field(default_factory=dict)
