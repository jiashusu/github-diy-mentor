from __future__ import annotations

from app.services.mentor import MENTOR_SYSTEM_PROMPT, fallback_mentor_result
from app.models import RepoCandidate, RepoFiles


def test_prompt_contains_required_sections():
    assert "懒人方案" in MENTOR_SYSTEM_PROMPT
    assert "AI增强版" in MENTOR_SYSTEM_PROMPT
    assert "避坑指南" in MENTOR_SYSTEM_PROMPT
    assert "overall_angle" in MENTOR_SYSTEM_PROMPT


def test_fallback_result_is_valid():
    repo = RepoCandidate(
        name="demo/budget",
        url="https://github.com/demo/budget",
        description="Track daily expenses",
        files=RepoFiles(readme="A tiny expense tracker"),
    )

    result = fallback_mentor_result(repo)

    assert result.overall_angle
    assert {idea.type for idea in result.ideas} == {"懒人方案", "AI增强版"}
    assert result.pitfalls
