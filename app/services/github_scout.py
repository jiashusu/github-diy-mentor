from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse

import httpx

from app.models import RepoCandidate, RepoFiles


GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"

TOPICS = [
    "lifestyle",
    "productivity",
    "home-automation",
    "creative-computing",
]

EXCLUDE_KEYWORDS = [
    "compiler",
    "runtime",
    "framework",
    "sdk",
    "deep learning",
    "machine learning library",
    "kubernetes",
    "database engine",
    "operating system",
    "kernel",
    "parser",
    "llvm",
    "distributed storage",
]

LIFE_KEYWORDS = [
    "recipe",
    "habit",
    "calendar",
    "todo",
    "note",
    "home",
    "automation",
    "pet",
    "photo",
    "wardrobe",
    "budget",
    "expense",
    "meal",
    "fitness",
    "garden",
    "organize",
    "dashboard",
    "tracker",
    "visual",
    "interactive",
    "family",
    "health",
    "shopping",
]

CHINESE_SEARCH_HINTS = {
    "整理衣柜": ["wardrobe", "closet", "clothes", "outfit"],
    "衣柜": ["wardrobe", "closet", "clothes", "outfit"],
    "穿搭": ["outfit", "wardrobe", "clothes"],
    "选菜": ["recipe", "meal planner", "food", "ingredient"],
    "做饭": ["recipe", "meal planner", "cooking", "ingredient"],
    "菜谱": ["recipe", "cookbook", "meal planner"],
    "记账": ["budget", "expense tracker", "finance"],
    "宠物": ["pet tracker", "pet care"],
    "收纳": ["organizer", "inventory", "home"],
}

VISUAL_MARKERS = ["![", "<img", "screenshot", "demo", ".gif", "youtube", "loom.com"]

SEARCH_QUERY = """
query SearchLifestyleRepos($query: String!, $first: Int!) {
  search(query: $query, type: REPOSITORY, first: $first) {
    nodes {
      ... on Repository {
        nameWithOwner
        url
        description
        homepageUrl
        createdAt
        pushedAt
        stargazerCount
        forkCount
        isArchived
        isFork
        primaryLanguage { name }
        repositoryTopics(first: 10) {
          nodes { topic { name } }
        }
        stargazers(first: 100, orderBy: {field: STARRED_AT, direction: DESC}) {
          totalCount
          edges { starredAt }
        }
        readme: object(expression: "HEAD:README.md") {
          ... on Blob { text }
        }
        packageJson: object(expression: "HEAD:package.json") {
          ... on Blob { text }
        }
        requirements: object(expression: "HEAD:requirements.txt") {
          ... on Blob { text }
        }
      }
    }
  }
}
"""


class GitHubScoutError(RuntimeError):
    pass


def _headers() -> dict[str, str]:
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise GitHubScoutError("Missing GITHUB_TOKEN. Add it to .env before discovering repositories.")
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "github-diy-mentor",
    }


def count_recent_stars(repo: dict[str, Any], since: datetime) -> int:
    count = 0
    for edge in repo.get("stargazers", {}).get("edges", []):
        starred_at_raw = edge.get("starredAt")
        if not starred_at_raw:
            continue
        starred_at = datetime.fromisoformat(starred_at_raw.replace("Z", "+00:00"))
        if starred_at >= since:
            count += 1
    return count


def _repo_text(repo: dict[str, Any]) -> str:
    readme = (repo.get("readme") or {}).get("text") or ""
    return " ".join(
        [
            repo.get("nameWithOwner") or "",
            repo.get("description") or "",
            readme[:12000],
        ]
    ).lower()


def normalize_search_terms(keyword: str | None) -> list[str]:
    if not keyword:
        return []
    cleaned = keyword.strip()
    if not cleaned:
        return []

    terms: list[str] = []
    matched_hint = False
    for chinese, hints in CHINESE_SEARCH_HINTS.items():
        if chinese in cleaned:
            matched_hint = True
            terms.extend(hints)
    if not matched_hint:
        terms.append(cleaned)
    return _dedupe_terms(terms)


def looks_life_useful(repo: dict[str, Any], search_terms: list[str] | None = None) -> bool:
    text = _repo_text(repo)
    if any(keyword in text for keyword in EXCLUDE_KEYWORDS):
        return False
    if search_terms and any(term.lower() in text for term in search_terms):
        return True
    return any(keyword in text for keyword in LIFE_KEYWORDS)


def has_visual_signal(repo: dict[str, Any]) -> bool:
    readme = ((repo.get("readme") or {}).get("text") or "").lower()
    return bool(repo.get("homepageUrl")) or any(marker in readme for marker in VISUAL_MARKERS)


def normalize_url(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlparse(value)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return value
    if parsed.netloc:
        return f"https:{value}" if value.startswith("//") else None
    if "." in value and " " not in value:
        return f"https://{value}"
    return None


def summarize_repo(repo: dict[str, Any], since: datetime, search_terms: list[str] | None = None) -> RepoCandidate:
    topics = [
        node["topic"]["name"]
        for node in repo.get("repositoryTopics", {}).get("nodes", [])
        if node.get("topic", {}).get("name")
    ]
    recent_stars = count_recent_stars(repo, since)
    visual_bonus = 10 if has_visual_signal(repo) else 0
    life_keyword_bonus = min(12, sum(2 for keyword in LIFE_KEYWORDS if keyword in _repo_text(repo)))
    search_bonus = min(20, sum(5 for term in search_terms or [] if term.lower() in _repo_text(repo)))
    trend_score = recent_stars * 3 + repo.get("stargazerCount", 0) * 0.01 + visual_bonus + life_keyword_bonus + search_bonus

    return RepoCandidate(
        name=repo["nameWithOwner"],
        url=normalize_url(repo.get("url")) or repo["url"],
        description=repo.get("description"),
        homepage_url=normalize_url(repo.get("homepageUrl")),
        language=(repo.get("primaryLanguage") or {}).get("name"),
        topics=topics,
        stars_total=repo.get("stargazerCount", 0),
        stars_last_7d_estimate=recent_stars,
        forks=repo.get("forkCount", 0),
        pushed_at=repo.get("pushedAt"),
        has_visual_signal=has_visual_signal(repo),
        trend_score=round(trend_score, 2),
        files=RepoFiles(
            readme=(repo.get("readme") or {}).get("text") or "",
            package_json=(repo.get("packageJson") or {}).get("text") or "",
            requirements_txt=(repo.get("requirements") or {}).get("text") or "",
        ),
    )


async def _search_topic(
    client: httpx.AsyncClient,
    topic: str,
    per_topic: int,
    since: datetime,
    search_terms: list[str] | None = None,
) -> list[RepoCandidate]:
    pushed_after = since.date().isoformat()
    keyword_part = search_terms[0] if search_terms else ""
    query = f"{keyword_part} topic:{topic} archived:false fork:false stars:>20 pushed:>={pushed_after}".strip()
    response = await client.post(
        GITHUB_GRAPHQL_URL,
        headers=_headers(),
        json={"query": SEARCH_QUERY, "variables": {"query": query, "first": per_topic}},
        timeout=30,
    )
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise GitHubScoutError(f"GitHub API request failed for topic:{topic}: {exc.response.status_code}") from exc
    payload = response.json()
    if payload.get("errors"):
        raise GitHubScoutError(str(payload["errors"]))

    candidates: list[RepoCandidate] = []
    for repo in payload["data"]["search"]["nodes"]:
        if not repo or repo.get("isArchived") or repo.get("isFork"):
            continue
        if not looks_life_useful(repo, search_terms):
            continue
        candidates.append(summarize_repo(repo, since, search_terms))
    return candidates


async def _search_keyword(
    client: httpx.AsyncClient,
    term: str,
    per_topic: int,
    since: datetime,
    search_terms: list[str],
) -> list[RepoCandidate]:
    query = f"{term} archived:false fork:false stars:>10"
    response = await client.post(
        GITHUB_GRAPHQL_URL,
        headers=_headers(),
        json={"query": SEARCH_QUERY, "variables": {"query": query, "first": per_topic}},
        timeout=30,
    )
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise GitHubScoutError(f"GitHub API request failed for keyword:{term}: {exc.response.status_code}") from exc
    payload = response.json()
    if payload.get("errors"):
        raise GitHubScoutError(str(payload["errors"]))

    candidates: list[RepoCandidate] = []
    for repo in payload["data"]["search"]["nodes"]:
        if not repo or repo.get("isArchived") or repo.get("isFork"):
            continue
        if not looks_life_useful(repo, search_terms):
            continue
        candidates.append(summarize_repo(repo, since, search_terms))
    return candidates


async def discover_repositories(
    days: int = 7,
    limit: int = 20,
    per_topic: int = 20,
    keyword: str | None = None,
) -> list[RepoCandidate]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    search_terms = normalize_search_terms(keyword)
    async with httpx.AsyncClient() as client:
        batches = await _run_topic_searches(client, since, per_topic, search_terms)

    by_name: dict[str, RepoCandidate] = {}
    for batch in batches:
        for repo in batch:
            by_name[repo.name] = repo

    return sorted(by_name.values(), key=lambda item: item.trend_score, reverse=True)[:limit]


async def _run_topic_searches(
    client: httpx.AsyncClient,
    since: datetime,
    per_topic: int,
    search_terms: list[str] | None = None,
) -> list[list[RepoCandidate]]:
    import asyncio

    results = await asyncio.gather(
        *[
            *[_search_topic(client, topic, per_topic, since, search_terms) for topic in TOPICS],
            *[
                _search_keyword(client, term, per_topic, since, search_terms)
                for term in (search_terms or [])[:3]
            ],
        ],
        return_exceptions=True,
    )
    successful_batches: list[list[RepoCandidate]] = []
    errors: list[str] = []
    for result in results:
        if isinstance(result, Exception):
            errors.append(str(result))
            continue
        successful_batches.append(result)

    if successful_batches:
        return successful_batches
    if errors:
        raise GitHubScoutError("; ".join(errors))
    return []


def _dedupe_terms(terms: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for term in terms:
        normalized = term.strip()
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(normalized)
    return result
