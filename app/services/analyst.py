from __future__ import annotations

import json
import re

from app.models import AnalysisResult, RepoCandidate
from app.services.translation import contains_cjk


def analyze_repo(repo: RepoCandidate, ui_language: str = "zh") -> AnalysisResult:
    readme = repo.files.readme or ""
    package_json = repo.files.package_json or ""
    requirements = repo.files.requirements_txt or ""

    language = (repo.language or "").lower()
    likely_commands: list[str] = []
    if ui_language == "en":
        macos = ["Install Git", "Prepare a code editor such as VS Code"]
        windows = ["Install Git for Windows", "Prepare a code editor such as VS Code"]
    else:
        macos = ["安装 Git", "准备一个代码编辑器，比如 VS Code"]
        windows = ["安装 Git for Windows", "准备一个代码编辑器，比如 VS Code"]
    notes: list[str] = []

    if package_json:
        macos.append("Install Node.js 18 or newer" if ui_language == "en" else "安装 Node.js 18 或更新版本")
        windows.append(
            "Install Node.js 18 or newer and confirm npm works"
            if ui_language == "en"
            else "安装 Node.js 18 或更新版本，并确认 npm 可用"
        )
        likely_commands.extend(["npm install", "npm run dev"])
    if requirements or language == "python":
        macos.append("Install Python 3.11 or newer" if ui_language == "en" else "安装 Python 3.11 或更新版本")
        windows.append(
            "Install Python 3.11 or newer and enable Add python.exe to PATH"
            if ui_language == "en"
            else "安装 Python 3.11 或更新版本，并勾选 Add python.exe to PATH"
        )
        likely_commands.extend(["python -m venv .venv", "pip install -r requirements.txt"])
    if not likely_commands:
        likely_commands.append(
            "Read the Installation or Quick Start section in README first"
            if ui_language == "en"
            else "先阅读 README 的 Installation 或 Quick Start 部分"
        )
        notes.append(
            "No package.json or requirements.txt was found, so the README is the source of truth."
            if ui_language == "en"
            else "没有发现 package.json 或 requirements.txt，运行方式需要以 README 为准。"
        )

    plain_summary = _plain_summary(repo, readme, ui_language)
    difficulty = _difficulty_score(repo, readme, package_json, requirements)

    if _mentions_docker(readme):
        macos.append("Optionally install Docker Desktop" if ui_language == "en" else "可选安装 Docker Desktop")
        windows.append(
            "Optionally install Docker Desktop; Windows may also need WSL2"
            if ui_language == "en"
            else "可选安装 Docker Desktop，Windows 可能还需要启用 WSL2"
        )
        likely_commands.append("docker compose up")
    if _needs_api_key(readme):
        notes.append(
            "The README mentions API keys or tokens, so setup likely requires a third-party account and environment variables."
            if ui_language == "en"
            else "README 提到了 API key 或 token，运行前大概率需要注册第三方服务并配置环境变量。"
        )

    return AnalysisResult(
        language="en" if ui_language == "en" else "zh",
        plain_summary=plain_summary,
        difficulty_score=difficulty,
        macos_requirements=_dedupe(macos),
        windows_requirements=_dedupe(windows),
        likely_run_commands=_dedupe(likely_commands),
        notes=notes,
    )


def _plain_summary(repo: RepoCandidate, readme: str, ui_language: str) -> str:
    if ui_language == "en":
        description = (repo.description_en or repo.description or "").strip().rstrip(".")
        if description:
            return description + "."
        first_sentence = _first_readme_sentence(readme)
        if first_sentence:
            return first_sentence
        return f"{repo.name} is an open source project, but the README does not provide enough detail to summarize it safely."

    description = (repo.description_zh or repo.description or "").strip().rstrip(".。")
    if description:
        return description + "。"

    first_sentence = _first_readme_sentence(readme)
    if first_sentence:
        return first_sentence if contains_cjk(first_sentence) else f"{repo.name} 的 README 主要介绍：{first_sentence}"

    return f"这是一个名叫 {repo.name} 的开源项目，当前 README 信息不多，需要打开项目页进一步确认用途。"


def _first_readme_sentence(readme: str) -> str:
    cleaned = re.sub(r"[#>*`_\[\]()]", " ", readme)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        return ""
    parts = re.split(r"(?<=[.!?。！？])\s+", cleaned)
    return parts[0][:180]


def _difficulty_score(repo: RepoCandidate, readme: str, package_json: str, requirements: str) -> int:
    score = 3
    if package_json:
        score += 1
        try:
            scripts = json.loads(package_json).get("scripts", {})
            if not scripts:
                score += 1
        except json.JSONDecodeError:
            score += 1
    if requirements:
        deps = [line for line in requirements.splitlines() if line.strip() and not line.strip().startswith("#")]
        score += min(3, max(1, len(deps) // 8))
    if _mentions_docker(readme):
        score += 1
    if _needs_api_key(readme):
        score += 2
    if any(word in readme.lower() for word in ["cuda", "gpu", "postgres", "redis", "ffmpeg"]):
        score += 2
    if repo.has_visual_signal:
        score -= 1
    return max(1, min(10, score))


def _mentions_docker(readme: str) -> bool:
    return "docker" in readme.lower() or "docker compose" in readme.lower()


def _needs_api_key(readme: str) -> bool:
    lowered = readme.lower()
    return any(marker in lowered for marker in ["api key", "apikey", "token", ".env", "secret"])


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result
