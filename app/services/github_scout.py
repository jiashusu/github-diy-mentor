from __future__ import annotations

import os
import re
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

TOPIC_FILTER_TERMS = {
    "all": [],
    "ai": ["ai", "llm", "agent", "automation"],
    "finance": ["finance", "trading", "quant", "market"],
    "home": ["home automation", "home-assistant", "iot", "smart home"],
    "media": ["photo", "video", "music", "media"],
    "game": ["game", "gaming", "emulator", "valorant"],
    "productivity": ["productivity", "todo", "notes", "organizer"],
    "humanities": ["knowledge", "wiki", "research", "social data"],
}

HARDWARE_TERMS = ["esp32", "raspberry pi", "arduino", "sensor", "mqtt", "camera", "iot", "hardware"]
SOFTWARE_ONLY_TERMS = ["web", "desktop", "cli", "python", "node", "browser", "app"]

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
    project_kind = _project_kind(repo)
    beginner_score = _beginner_score(repo)
    recommendation_reasons = _recommendation_reasons(repo, recent_stars, project_kind, beginner_score)

    return RepoCandidate(
        name=repo["nameWithOwner"],
        url=normalize_url(repo.get("url")) or repo["url"],
        description=repo.get("description"),
        description_en=repo.get("description"),
        homepage_url=normalize_url(repo.get("homepageUrl")),
        language=(repo.get("primaryLanguage") or {}).get("name"),
        topics=topics,
        stars_total=repo.get("stargazerCount", 0),
        stars_last_7d_estimate=recent_stars,
        forks=repo.get("forkCount", 0),
        pushed_at=repo.get("pushedAt"),
        has_visual_signal=has_visual_signal(repo),
        trend_score=round(trend_score, 2),
        recommendation_reasons=recommendation_reasons,
        project_kind=project_kind,
        beginner_score=beginner_score,
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
    language_filter: str = "all",
) -> list[RepoCandidate]:
    pushed_after = since.date().isoformat()
    keyword_part = search_terms[0] if search_terms else ""
    language_part = _language_query_part(language_filter)
    query = f"{keyword_part} topic:{topic} {language_part} archived:false fork:false stars:>20 pushed:>={pushed_after}".strip()
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
        if not _matches_language_filter(repo, language_filter):
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
    language_filter: str = "all",
) -> list[RepoCandidate]:
    language_part = _language_query_part(language_filter)
    query = f"{term} {language_part} archived:false fork:false stars:>10"
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
        if not _matches_language_filter(repo, language_filter):
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
    language_filter: str = "all",
    topic_filter: str = "all",
    sort_mode: str = "trending",
    exclude_names: set[str] | None = None,
) -> list[RepoCandidate]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    search_terms = _dedupe_terms([*normalize_search_terms(keyword), *TOPIC_FILTER_TERMS.get(topic_filter, [])])
    async with httpx.AsyncClient() as client:
        fetch_size = max(per_topic, min(50, limit + len(exclude_names or set())))
        batches = await _run_topic_searches(client, since, fetch_size, search_terms, language_filter)

    by_name: dict[str, RepoCandidate] = {}
    excluded = exclude_names or set()
    for batch in batches:
        for repo in batch:
            if repo.name in excluded:
                continue
            by_name[repo.name] = repo

    return sorted(
        by_name.values(),
        key=lambda item: _sort_score(item, sort_mode),
        reverse=True,
    )[:limit]


async def _run_topic_searches(
    client: httpx.AsyncClient,
    since: datetime,
    per_topic: int,
    search_terms: list[str] | None = None,
    language_filter: str = "all",
) -> list[list[RepoCandidate]]:
    import asyncio

    results = await asyncio.gather(
        *[
            *[_search_topic(client, topic, per_topic, since, search_terms, language_filter) for topic in TOPICS],
            *[
                _search_keyword(client, term, per_topic, since, search_terms, language_filter)
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


def _language_query_part(language_filter: str) -> str:
    return ""


def _matches_language_filter(repo: dict[str, Any], language_filter: str) -> bool:
    if language_filter == "all":
        return True
    text = _repo_text(repo)
    has_cjk = bool(re.search(r"[\u3400-\u9fff]", text))
    primary_language = ((repo.get("primaryLanguage") or {}).get("name") or "").lower()
    if language_filter == "zh":
        return has_cjk
    if language_filter == "en":
        return not has_cjk
    if language_filter == "other":
        return primary_language not in {"python", "typescript", "javascript", "go", "rust", "java", "c++", "c#", "swift", "kotlin"}
    return True


def _sort_score(repo: RepoCandidate, sort_mode: str) -> float:
    text = " ".join([repo.description or "", repo.files.readme[:5000], " ".join(repo.topics)]).lower()
    if sort_mode == "stars":
        return float(repo.stars_total)
    if sort_mode == "beginner":
        dependency_penalty = len(repo.files.requirements_txt.splitlines()) * 0.2 + len(repo.files.package_json) / 3000
        docker_bonus = 4 if "docker" in text else 0
        return 30 + docker_bonus + repo.has_visual_signal * 5 - dependency_penalty + repo.stars_last_7d_estimate
    if sort_mode == "hardware":
        return repo.trend_score + sum(12 for term in HARDWARE_TERMS if term in text)
    if sort_mode == "software":
        hardware_penalty = sum(10 for term in HARDWARE_TERMS if term in text)
        software_bonus = sum(6 for term in SOFTWARE_ONLY_TERMS if term in text)
        return repo.trend_score + software_bonus - hardware_penalty
    giant_penalty = min(35, repo.stars_total / 2500)
    return repo.trend_score + repo.beginner_score * 1.2 - giant_penalty


def recommendation_summary(repo: RepoCandidate, ui_language: str = "zh") -> str:
    reasons = repo.recommendation_reasons[:4]
    if ui_language == "en":
        if not reasons:
            return "This project matched the current search and ranking filters."
        return "Worth checking because: " + ", ".join(reasons) + "."
    if not reasons:
        return "它命中了当前搜索和筛选条件，值得进一步查看。"
    return "值得看，因为：" + "、".join(reasons) + "。"


def _project_kind(repo: dict[str, Any]) -> str:
    text = _repo_text(repo)
    has_hardware = any(term in text for term in HARDWARE_TERMS)
    has_software = any(term in text for term in SOFTWARE_ONLY_TERMS)
    if has_hardware and has_software:
        return "mixed"
    if has_hardware:
        return "hardware"
    if has_software:
        return "software"
    return "unknown"


def _beginner_score(repo: dict[str, Any]) -> int:
    readme = ((repo.get("readme") or {}).get("text") or "").lower()
    package_json = (repo.get("packageJson") or {}).get("text") or ""
    requirements = (repo.get("requirements") or {}).get("text") or ""
    score = 5
    if "docker" in readme:
        score += 2
    if any(marker in readme for marker in ["quick start", "quickstart", "installation", "getting started"]):
        score += 1
    if has_visual_signal(repo):
        score += 1
    if len(package_json) > 6000 or len(requirements.splitlines()) > 25:
        score -= 2
    if any(term in readme for term in HARDWARE_TERMS):
        score -= 1
    return max(1, min(10, score))


def _recommendation_reasons(repo: dict[str, Any], recent_stars: int, project_kind: str, beginner_score: int) -> list[str]:
    readme = ((repo.get("readme") or {}).get("text") or "").lower()
    reasons: list[str] = []
    if recent_stars > 0:
        reasons.append(f"7日 +{recent_stars} stars")
    if has_visual_signal(repo):
        reasons.append("有截图/demo")
    if "docker" in readme:
        reasons.append("Docker 可运行")
    if beginner_score >= 7:
        reasons.append("新手友好")
    if project_kind == "hardware":
        reasons.append("硬件项目")
    elif project_kind == "software":
        reasons.append("纯软工具")
    elif project_kind == "mixed":
        reasons.append("软硬结合")
    if len(readme) > 800:
        reasons.append("README 较清晰")
    return reasons[:5]


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
