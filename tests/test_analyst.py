from __future__ import annotations

from app.models import RepoCandidate, RepoFiles
from app.services.analyst import analyze_repo


def test_python_requirements_are_reported():
    repo = RepoCandidate(
        name="demo/file-sorter",
        url="https://github.com/demo/file-sorter",
        description="Sort files into folders",
        language="Python",
        files=RepoFiles(readme="Simple file organizer", requirements_txt="watchdog\nopenai\n"),
    )

    result = analyze_repo(repo)

    assert "Python 3.11" in " ".join(result.macos_requirements)
    assert 1 <= result.difficulty_score <= 10
    assert any("pip install" in command for command in result.likely_run_commands)


def test_node_requirements_are_reported():
    repo = RepoCandidate(
        name="demo/recipe-ui",
        url="https://github.com/demo/recipe-ui",
        description="Recipe dashboard",
        language="TypeScript",
        files=RepoFiles(package_json='{"scripts":{"dev":"vite --host 0.0.0.0"}}'),
    )

    result = analyze_repo(repo)

    assert "Node.js" in " ".join(result.windows_requirements)
    assert "npm install" in result.likely_run_commands


def test_chinese_summary_does_not_use_fixed_prefix():
    repo = RepoCandidate(
        name="demo/home",
        url="https://github.com/demo/home",
        description="Open source home automation",
        description_zh="开源智能家居自动化工具",
        language="Python",
    )

    result = analyze_repo(repo, "zh")

    assert result.language == "zh"
    assert result.plain_summary == "开源智能家居自动化工具。"
    assert "它像是一个帮你处理日常事务的小工具" not in result.plain_summary


def test_english_summary_stays_english():
    repo = RepoCandidate(
        name="demo/home",
        url="https://github.com/demo/home",
        description="Open source home automation",
        language="Python",
    )

    result = analyze_repo(repo, "en")

    assert result.language == "en"
    assert result.plain_summary == "Open source home automation."
    assert "安装" not in " ".join(result.macos_requirements)
