from __future__ import annotations

import json
from pathlib import Path

from app.models import FullAnalysisResult, RepoCandidate


ROOT_DIR = Path(__file__).resolve().parents[2]
CACHE_PATH = ROOT_DIR / "data" / "analysis_cache.json"


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


def _read_cache() -> dict:
    if not CACHE_PATH.exists():
        return {}
    try:
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
