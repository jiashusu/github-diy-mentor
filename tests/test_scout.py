from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.services.github_scout import count_recent_stars, looks_life_useful, normalize_search_terms, summarize_repo


def repo_fixture(**overrides):
    now = datetime.now(timezone.utc)
    repo = {
        "nameWithOwner": "demo/home-helper",
        "url": "https://github.com/demo/home-helper",
        "description": "A home automation dashboard for daily chores",
        "homepageUrl": "https://example.com",
        "stargazerCount": 120,
        "forkCount": 4,
        "pushedAt": now.isoformat(),
        "isArchived": False,
        "isFork": False,
        "primaryLanguage": {"name": "Python"},
        "repositoryTopics": {"nodes": [{"topic": {"name": "home-automation"}}]},
        "stargazers": {
            "edges": [
                {"starredAt": now.isoformat()},
                {"starredAt": (now - timedelta(days=10)).isoformat()},
            ]
        },
        "readme": {"text": "![screenshot](demo.png)\nTrack home chores and family tasks."},
        "packageJson": None,
        "requirements": {"text": "fastapi\n"},
    }
    repo.update(overrides)
    return repo


def test_count_recent_stars():
    since = datetime.now(timezone.utc) - timedelta(days=7)
    assert count_recent_stars(repo_fixture(), since) == 1


def test_filters_low_level_frameworks():
    repo = repo_fixture(description="A compiler framework and parser runtime")
    assert looks_life_useful(repo) is False


def test_summarize_repo_scores_visual_lifestyle_project():
    since = datetime.now(timezone.utc) - timedelta(days=7)
    summary = summarize_repo(repo_fixture(), since)
    assert summary.name == "demo/home-helper"
    assert summary.has_visual_signal is True
    assert summary.stars_last_7d_estimate == 1
    assert summary.trend_score > 10


def test_chinese_keyword_expands_to_github_terms():
    terms = normalize_search_terms("整理衣柜")
    assert "wardrobe" in terms
    assert "closet" in terms
