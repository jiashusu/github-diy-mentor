from __future__ import annotations

from app.models import FullAnalysisResult, RepoCandidate
from app.services.github_scout import recommendation_summary


def analysis_to_markdown(result: FullAnalysisResult, ui_language: str = "zh") -> str:
    repo = result.repo
    analysis = result.analysis
    mentor = result.mentor
    lines = [
        f"# {repo.name}",
        "",
        f"- GitHub: {repo.url}",
        f"- Stars: {repo.stars_total}",
        f"- Language: {repo.language or 'Unknown'}",
        f"- Kind: {repo.project_kind}",
        "",
        "## Why It Is Worth Checking" if ui_language == "en" else "## 为什么值得看",
        "",
        result.recommendation_summary or recommendation_summary(repo, ui_language),
        "",
        "## Summary" if ui_language == "en" else "## 一句话简介",
        "",
        analysis.plain_summary,
        "",
        "## DIY Ideas" if ui_language == "en" else "## DIY 改造建议",
        "",
    ]
    for idea in mentor.ideas:
        lines.extend(
            [
                f"### {idea.title}",
                "",
                f"- Type: {idea.type}",
                f"- Difficulty: {idea.difficulty}",
                f"- Direction: {idea.direction}",
                f"- For: {idea.for_whom}",
                f"- AI capability: {idea.ai_capability}",
                "",
                "Steps:",
                *[f"{idx + 1}. {step}" for idx, step in enumerate(idea.minimum_steps)],
                "",
            ]
        )
    lines.extend(["## Pitfalls" if ui_language == "en" else "## 避坑指南", ""])
    for pitfall in mentor.pitfalls:
        lines.append(f"- **{pitfall.platform}**: {pitfall.symptom}；{pitfall.fix}")
    return "\n".join(lines).strip() + "\n"


def export_session_markdown(
    repos: list[RepoCandidate],
    analyses: list[FullAnalysisResult],
    ui_language: str = "zh",
) -> str:
    title = "# GitHub DIY Mentor Export" if ui_language == "en" else "# GitHub DIY Mentor 导出"
    lines = [title, ""]
    if repos:
        lines.extend(["## Project List" if ui_language == "en" else "## 项目列表", ""])
        for repo in repos:
            lines.append(f"- **{repo.name}**: {repo.description_zh or repo.description or ''} ({repo.url})")
        lines.append("")
    for result in analyses:
        lines.append("---")
        lines.append("")
        lines.append(analysis_to_markdown(result, ui_language))
    return "\n".join(lines).strip() + "\n"
