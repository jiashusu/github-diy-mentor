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
