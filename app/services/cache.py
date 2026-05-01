from __future__ import annotations

import json
import time
from pathlib import Path

from app.models import FullAnalysisResult, RepoCandidate


ROOT_DIR = Path(__file__).resolve().parents[2]
CACHE_PATH = ROOT_DIR / "data" / "analysis_cache.json"
DISCOVERY_CACHE_PATH = ROOT_DIR / "data" / "discovery_cache.json"
TRANSLATION_CACHE_PATH = ROOT_DIR / "data" / "translation_cache.json"
FAVORITES_PATH = ROOT_DIR / "data" / "favorites.json"
CACHE_TTL_SECONDS = 3600


def analysis_cache_key(repo: RepoCandidate, ui_language: str) -> str:
    pushed_at = repo.pushed_at or "unknown"
    return f"{repo.name}|{pushed_at}|{ui_language}"


def get_cached_analysis(repo: RepoCandidate, ui_language: str) -> FullAnalysisResult | None:
    data = _read_cache()
    raw = data.get(analysis_cache_key(repo, ui_language))
    if not raw:
        return None
    try:
        result = FullAnalysisResult.model_validate(raw)
        result.cached = True
        return result
    except Exception:
        return None


def set_cached_analysis(repo: RepoCandidate, ui_language: str, result: FullAnalysisResult) -> None:
    data = _read_cache()
    stored = result.model_dump(mode="json")
    stored["cached"] = False
    data[analysis_cache_key(repo, ui_language)] = stored
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def discovery_cache_key(params: dict) -> str:
    return json.dumps(params, ensure_ascii=False, sort_keys=True)


def get_cached_discovery(params: dict) -> list[RepoCandidate] | None:
    data = _read_json(DISCOVERY_CACHE_PATH)
    raw = data.get(discovery_cache_key(params))
    if not raw:
        return None
    if time.time() - raw.get("created_at", 0) > CACHE_TTL_SECONDS:
        return None
    try:
        return [RepoCandidate.model_validate(item) for item in raw.get("repos", [])]
    except Exception:
        return None


def set_cached_discovery(params: dict, repos: list[RepoCandidate]) -> None:
    data = _read_json(DISCOVERY_CACHE_PATH)
    data[discovery_cache_key(params)] = {
        "created_at": time.time(),
        "repos": [repo.model_dump(mode="json") for repo in repos],
    }
    _write_json(DISCOVERY_CACHE_PATH, data)


def get_cached_translations(texts: dict[str, str], target_language: str) -> tuple[dict[str, str], dict[str, str]]:
    data = _read_json(TRANSLATION_CACHE_PATH)
    cached: dict[str, str] = {}
    missing: dict[str, str] = {}
    for key, value in texts.items():
        cache_key = f"{target_language}|{value}"
        if cache_key in data:
            cached[key] = data[cache_key]
        else:
            missing[key] = value
    return cached, missing


def set_cached_translations(texts: dict[str, str], translated: dict[str, str], target_language: str) -> None:
    data = _read_json(TRANSLATION_CACHE_PATH)
    for key, source in texts.items():
        if key in translated:
            data[f"{target_language}|{source}"] = translated[key]
    _write_json(TRANSLATION_CACHE_PATH, data)


def list_favorites() -> list[RepoCandidate]:
    data = _read_json(FAVORITES_PATH)
    repos = data.get("repos", {})
    result: list[RepoCandidate] = []
    for raw in repos.values():
        try:
            result.append(RepoCandidate.model_validate(raw))
        except Exception:
            continue
    return sorted(result, key=lambda repo: repo.name.lower())


def add_favorite(repo: RepoCandidate) -> list[RepoCandidate]:
    data = _read_json(FAVORITES_PATH)
    repos = data.setdefault("repos", {})
    repos[repo.name] = repo.model_dump(mode="json")
    _write_json(FAVORITES_PATH, data)
    return list_favorites()


def remove_favorite(repo_name: str) -> list[RepoCandidate]:
    data = _read_json(FAVORITES_PATH)
    data.setdefault("repos", {}).pop(repo_name, None)
    _write_json(FAVORITES_PATH, data)
    return list_favorites()


def _read_cache() -> dict:
    return _read_json(CACHE_PATH)


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
