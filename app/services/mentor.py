from __future__ import annotations

import json
import os

from app.models import AnalysisResult, MentorResult, RepoCandidate


MENTOR_SYSTEM_PROMPT = """你是“AI DIY 导师”，目标读者是会使用电脑、愿意折腾开源项目、但不是专业程序员的普通用户。

你的任务：提出 2-3 个“加入 AI 后更好玩、更实用”的 DIY 改造建议。建议必须具体、可操作、对非专业人士友好，不能只说概念。

输出要求：
1. 全部使用简体中文。
2. 不要堆专业术语；必须解释普通用户能理解的价值。
3. 每个方案都要说明：
   - 改造方向：一句话说明要把项目变成什么。
   - 适合谁：具体到生活场景。
   - 最小实现方式：优先给“不大改代码”的做法。
   - 需要接入的 AI 能力：如文本总结、图片识别、语音转文字、结构化抽取、推荐生成。
   - 可能要改的文件或模块：如果无法判断，说明“需要先找到处理 XXX 的文件”。
   - DIY 难度：低 / 中 / 高，并说明原因。
4. 必须包含这三类内容：
   - 懒人方案：尽量通过配置、提示词、现成 API、Zapier/Make/快捷指令等方式实现。
   - AI增强版：需要少量改代码，但能明显提升项目价值。
   - 避坑指南：预测 macOS / Windows 部署、API key、依赖安装、文件权限、Node/Python 版本等常见问题。
5. 不要编造项目不存在的功能。如果 README 信息不足，要明确写“基于当前 README 只能推测”。
6. 每条建议都要避免“做一个 AI 助手”这种空泛说法，必须绑定项目原本功能。

请严格返回 JSON：

{
  "overall_angle": "这个项目最值得 AI 改造的方向，用一句话说明",
  "ideas": [
    {
      "type": "懒人方案 | AI增强版",
      "title": "短标题",
      "direction": "改造方向",
      "for_whom": "适合谁和什么生活场景",
      "minimum_steps": ["步骤1", "步骤2", "步骤3"],
      "ai_capability": "需要的 AI 能力",
      "files_or_modules_to_check": ["可能相关的文件或模块"],
      "difficulty": "低 | 中 | 高",
      "why_this_is_useful": "为什么这个改造有生活价值"
    }
  ],
  "pitfalls": [
    {
      "platform": "macOS | Windows | 通用",
      "symptom": "用户可能看到的报错或现象",
      "likely_cause": "可能原因",
      "fix": "普通用户能照做的解决办法"
    }
  ]
}
"""


def build_project_context(repo: RepoCandidate, analysis: AnalysisResult | None = None) -> str:
    readme_excerpt = (repo.files.readme or "")[:5000]
    package_excerpt = (repo.files.package_json or "")[:1800]
    requirements_excerpt = (repo.files.requirements_txt or "")[:1800]
    return json.dumps(
        {
            "项目名称": repo.name,
            "GitHub": str(repo.url),
            "简介": repo.description,
            "主页": str(repo.homepage_url) if repo.homepage_url else None,
            "主要语言": repo.language,
            "topics": repo.topics,
            "stars_total": repo.stars_total,
            "stars_last_7d_estimate": repo.stars_last_7d_estimate,
            "has_visual_signal": repo.has_visual_signal,
            "analysis": analysis.model_dump() if analysis else None,
            "README摘要": readme_excerpt,
            "package_json摘要": package_excerpt,
            "requirements_txt摘要": requirements_excerpt,
        },
        ensure_ascii=False,
        indent=2,
    )


async def generate_mentor_result(repo: RepoCandidate, analysis: AnalysisResult | None = None) -> MentorResult:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return fallback_mentor_result(repo, analysis)

    try:
        from openai import AsyncOpenAI
    except ImportError:
        return fallback_mentor_result(repo, analysis)

    client = AsyncOpenAI(api_key=api_key, timeout=30)
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    try:
        response = await client.chat.completions.create(
            model=model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": MENTOR_SYSTEM_PROMPT},
                {"role": "user", "content": f"项目信息如下：\n{build_project_context(repo, analysis)}"},
            ],
            temperature=0.7,
        )
        content = response.choices[0].message.content or "{}"
        return MentorResult.model_validate_json(content)
    except Exception:
        return fallback_mentor_result(repo, analysis)


def fallback_mentor_result(repo: RepoCandidate, analysis: AnalysisResult | None = None) -> MentorResult:
    context_note = "基于当前 README 只能推测，建议先确认项目的主要输入和输出位置。"
    original_use = analysis.plain_summary if analysis else (repo.description or repo.name)
    return MentorResult.model_validate(
        {
            "overall_angle": f"把“{original_use}”升级成能理解用户真实意图的半自动生活工具。",
            "ideas": [
                {
                    "type": "懒人方案",
                    "title": "用 AI 先生成配置和使用模板",
                    "direction": "不改核心代码，让 AI 根据你的生活场景生成项目配置、标签或规则。",
                    "for_whom": "适合想快速试用项目、但不想研究每个配置项的普通用户。",
                    "minimum_steps": [
                        "把 README 和示例配置复制给 AI。",
                        "说明自己的具体场景，比如家庭整理、记账、菜谱或待办。",
                        "让 AI 输出可直接粘贴的配置文件或规则清单。",
                    ],
                    "ai_capability": "文本理解、规则生成、配置生成",
                    "files_or_modules_to_check": ["README.md", "config.example", ".env.example"],
                    "difficulty": "低",
                    "why_this_is_useful": "先把最费脑的配置过程交给 AI，普通用户更容易跑起来并看到效果。",
                },
                {
                    "type": "AI增强版",
                    "title": "把手动输入升级成自然语言输入",
                    "direction": "让用户用一句话描述需求，再由 AI 转成项目原本需要的结构化数据。",
                    "for_whom": "适合经常记录、整理或筛选生活信息的人。",
                    "minimum_steps": [
                        "找到项目里处理用户输入或数据导入的文件。",
                        "新增一个调用 LLM API 的小函数，把自然语言转成 JSON。",
                        "把生成的 JSON 交给项目原本的处理逻辑。",
                    ],
                    "ai_capability": "自然语言理解、结构化抽取",
                    "files_or_modules_to_check": ["需要先找到处理用户输入、导入或分类的文件"],
                    "difficulty": "中",
                    "why_this_is_useful": "用户不用学习项目内部格式，用自己的话就能完成原本繁琐的输入。",
                },
            ],
            "pitfalls": [
                {
                    "platform": "通用",
                    "symptom": "AI 功能没有反应，或提示 authentication failed。",
                    "likely_cause": "没有配置 OPENAI_API_KEY，或者 .env 没有被程序读取。",
                    "fix": "在项目根目录创建 .env，写入 OPENAI_API_KEY=你的密钥，然后重启服务。",
                },
                {
                    "platform": "Windows",
                    "symptom": "python 或 npm 不是内部或外部命令。",
                    "likely_cause": "安装时没有加入 PATH，或终端没有重启。",
                    "fix": "重新安装 Python/Node 并勾选加入 PATH，安装后打开新的 PowerShell 再运行命令。",
                },
                {
                    "platform": "macOS",
                    "symptom": "安装依赖时报 permission denied。",
                    "likely_cause": "把依赖装进了系统 Python，权限不够。",
                    "fix": "在项目目录先运行 python -m venv .venv，再激活虚拟环境后安装依赖。",
                },
            ],
        }
    )
