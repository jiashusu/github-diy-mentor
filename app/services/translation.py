from __future__ import annotations

import json
import os
import re


def contains_cjk(text: str | None) -> bool:
    if not text:
        return False
    return bool(re.search(r"[\u3400-\u9fff]", text))


def localize_static(texts: dict[str, str], ui_language: str) -> dict[str, str]:
    if ui_language != "zh":
        return texts
    return {key: _simple_zh(value) for key, value in texts.items()}


async def translate_short_texts(texts: dict[str, str], target_language: str) -> dict[str, str]:
    cleaned = {key: value for key, value in texts.items() if value}
    if not cleaned:
        return {}
    if target_language == "en":
        return cleaned

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return localize_static(cleaned, target_language)

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=api_key, timeout=20)
        response = await client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Translate GitHub project descriptions into natural Simplified Chinese. "
                        "Keep repository names, programming languages, commands, API names, and product names in English. "
                        "Return JSON with the exact same keys. Do not add commentary."
                    ),
                },
                {"role": "user", "content": json.dumps(cleaned, ensure_ascii=False)},
            ],
            temperature=0.2,
        )
        content = response.choices[0].message.content or "{}"
        translated = json.loads(content)
        return {key: str(translated.get(key, value)) for key, value in cleaned.items()}
    except Exception:
        return localize_static(cleaned, target_language)


def _simple_zh(text: str) -> str:
    replacements = {
        "Open source home automation that puts local control and privacy first.": "开源智能家居自动化平台，强调本地控制和隐私优先。",
        "home automation": "智能家居自动化",
        "dashboard": "仪表盘",
        "daily chores": "日常家务",
        "Recipe dashboard": "菜谱仪表盘",
        "Sort files into folders": "把文件自动整理到文件夹",
        "Track daily expenses": "记录日常开销",
    }
    result = text
    for source, target in replacements.items():
        result = result.replace(source, target)
    return result
