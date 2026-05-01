from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.models import (
    AnalyzeRequest,
    AnalysisResult,
    FullAnalysisRequest,
    FullAnalysisResult,
    MentorRequest,
    MentorResult,
    RepoCandidate,
)
from app.services.cache import get_cached_analysis, set_cached_analysis
from app.services.analyst import analyze_repo
from app.services.github_scout import GitHubScoutError, discover_repositories
from app.services.mentor import fallback_mentor_result, generate_mentor_result
from app.services.translation import translate_short_texts
import httpx


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="GitHub DIY Mentor", version="0.1.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/discover", response_model=list[RepoCandidate])
async def discover(
    days: int = Query(default=7, ge=1, le=30),
    limit: int = Query(default=20, ge=1, le=50),
    q: str | None = Query(default=None, max_length=80),
    ui_language: str = Query(default="zh", pattern="^(zh|en)$"),
    language_filter: str = Query(default="all", pattern="^(all|zh|en|other)$"),
    topic_filter: str = Query(default="all", pattern="^(all|ai|finance|home|media|game|productivity|humanities)$"),
    sort_mode: str = Query(default="trending", pattern="^(trending|stars|beginner|hardware|software)$"),
) -> list[RepoCandidate]:
    try:
        repos = await discover_repositories(
            days=days,
            limit=limit,
            keyword=q,
            language_filter=language_filter,
            topic_filter=topic_filter,
            sort_mode=sort_mode,
        )
        if ui_language == "zh":
            translations = await translate_short_texts(
                {repo.name: repo.description or "" for repo in repos if repo.description},
                "zh",
            )
            for repo in repos:
                repo.description_en = repo.description
                repo.description_zh = translations.get(repo.name) or repo.description
        else:
            for repo in repos:
                repo.description_en = repo.description
        return repos
    except GitHubScoutError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"GitHub API 暂时不可用：{exc}") from exc


@app.post("/api/analyze", response_model=AnalysisResult)
async def analyze(request: AnalyzeRequest) -> AnalysisResult:
    return analyze_repo(request.repo)


@app.post("/api/mentor", response_model=MentorResult)
async def mentor(request: MentorRequest) -> MentorResult:
    return await generate_mentor_result(request.repo, request.analysis)


@app.post("/api/full-analysis", response_model=FullAnalysisResult)
async def full_analysis(request: FullAnalysisRequest) -> FullAnalysisResult:
    cached = get_cached_analysis(request.repo, request.ui_language)
    if cached:
        return cached

    try:
        analysis = analyze_repo(request.repo, request.ui_language)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"项目基础分析失败：{exc}") from exc

    try:
        mentor_result = await generate_mentor_result(request.repo, analysis, request.ui_language)
    except Exception:
        mentor_result = fallback_mentor_result(request.repo, analysis, request.ui_language)
    result = FullAnalysisResult(repo=request.repo, analysis=analysis, mentor=mentor_result, cached=False)
    set_cached_analysis(request.repo, request.ui_language, result)
    return result
