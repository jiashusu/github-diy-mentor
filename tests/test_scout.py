from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from app.services.github_scout import (
    LANGUAGE_FILTER_VALUES,
    TOPIC_FILTER_VALUES,
    _matches_language_filter,
    _sort_score,
    count_recent_stars,
    discover_repositories,
    looks_life_useful,
    normalize_filter_values,
    normalize_search_terms,
    summarize_repo,
)


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
    assert summary.recommendation_reasons
    assert summary.project_kind in {"software", "hardware", "mixed", "unknown"}
    assert 1 <= summary.beginner_score <= 10


def test_chinese_keyword_expands_to_github_terms():
    terms = normalize_search_terms("整理衣柜")
    assert "wardrobe" in terms
    assert "closet" in terms


def test_sort_modes_score_expected_signals():
    since = datetime.now(timezone.utc) - timedelta(days=7)
    summary = summarize_repo(repo_fixture(description="ESP32 smart home sensor dashboard"), since)
    assert _sort_score(summary, "stars") == summary.stars_total
    assert _sort_score(summary, "hardware") > summary.trend_score


def test_discover_excludes_seen_repositories(monkeypatch):
    since = datetime.now(timezone.utc) - timedelta(days=7)
    first = summarize_repo(repo_fixture(nameWithOwner="demo/first"), since)
    second = summarize_repo(repo_fixture(nameWithOwner="demo/second"), since)

    async def fake_run_topic_searches(*args, **kwargs):
        return [[first, second]]

    monkeypatch.setattr("app.services.github_scout._run_topic_searches", fake_run_topic_searches)

    repos = asyncio.run(discover_repositories(limit=2, exclude_names={"demo/first"}))

    assert [repo.name for repo in repos] == ["demo/second"]


def test_normalizes_multi_select_filters():
    assert normalize_filter_values("zh,en", LANGUAGE_FILTER_VALUES) == ["en", "zh"]
    assert normalize_filter_values("all,zh", LANGUAGE_FILTER_VALUES) == ["all"]
    assert normalize_filter_values("bad", TOPIC_FILTER_VALUES) == ["all"]


def test_multi_topic_filters_merge_keywords(monkeypatch):
    captured = {}

    async def fake_run_topic_searches(client, since, per_topic, search_terms, language_filter):
        captured["search_terms"] = search_terms
        captured["language_filter"] = language_filter
        return [[]]

    monkeypatch.setattr("app.services.github_scout._run_topic_searches", fake_run_topic_searches)

    asyncio.run(discover_repositories(topic_filter=["ai", "home"], language_filter=["zh", "en"]))

    assert "llm" in captured["search_terms"]
    assert "smart home" in captured["search_terms"]
    assert captured["language_filter"] == ["en", "zh"]


def test_multi_language_filter_uses_or_semantics():
    chinese_repo = repo_fixture(description="中文 家庭自动化")
    english_repo = repo_fixture(description="Home automation dashboard")

    assert _matches_language_filter(chinese_repo, ["zh", "en"]) is True
    assert _matches_language_filter(english_repo, ["zh", "en"]) is True
    assert _matches_language_filter(chinese_repo, ["en"]) is False
