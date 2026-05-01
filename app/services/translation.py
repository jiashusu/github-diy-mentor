from __future__ import annotations

import json
import os
import re

from app.services.cache import get_cached_translations, set_cached_translations


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
    cached, missing = get_cached_translations(cleaned, target_language)
    if not missing:
        return cached

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        translated = localize_static(missing, target_language)
        set_cached_translations(missing, translated, target_language)
        return {**cached, **translated}

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
                {"role": "user", "content": json.dumps(missing, ensure_ascii=False)},
            ],
            temperature=0.2,
        )
        content = response.choices[0].message.content or "{}"
        translated = json.loads(content)
        result = {key: str(translated.get(key, value)) for key, value in missing.items()}
    except Exception:
        result = localize_static(missing, target_language)
    set_cached_translations(missing, result, target_language)
    return {**cached, **result}


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
