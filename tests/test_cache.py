from __future__ import annotations

from app.models import AnalysisResult, FullAnalysisResult, MentorResult, RepoCandidate
from app.services import cache


def test_analysis_cache_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "CACHE_PATH", tmp_path / "analysis_cache.json")
    repo = RepoCandidate(
        name="demo/cache",
        url="https://github.com/demo/cache",
        description="Cache demo",
        pushed_at="2026-05-01T00:00:00Z",
    )
    result = FullAnalysisResult(
        repo=repo,
        analysis=AnalysisResult(
            language="zh",
            plain_summary="缓存测试。",
            difficulty_score=3,
            macos_requirements=["安装 Git"],
            windows_requirements=["安装 Git for Windows"],
            likely_run_commands=["README"],
        ),
        mentor=MentorResult(
            overall_angle="缓存测试",
            ideas=[
                {
                    "type": "懒人方案",
                    "title": "模板",
                    "direction": "生成模板",
                    "for_whom": "普通用户",
                    "minimum_steps": ["复制 README"],
                    "ai_capability": "文本生成",
                    "files_or_modules_to_check": ["README.md"],
                    "difficulty": "低",
                    "why_this_is_useful": "省 token",
                }
            ],
            pitfalls=[
                {
                    "platform": "通用",
                    "symptom": "重复生成",
                    "likely_cause": "没有缓存",
                    "fix": "读取缓存",
                }
            ],
        ),
        cached=False,
    )

    assert cache.get_cached_analysis(repo, "zh") is None
    cache.set_cached_analysis(repo, "zh", result)
    cached = cache.get_cached_analysis(repo, "zh")

    assert cached is not None
    assert cached.cached is True
    assert cached.analysis.plain_summary == "缓存测试。"
