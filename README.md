# GitHub DIY Mentor

GitHub DIY Mentor is a small FastAPI web app that finds practical, playful GitHub projects and explains how ordinary users can improve them with AI.

This is the first raw version of the project: simple local UI, GitHub discovery, README/dependency analysis, and AI-generated DIY upgrade ideas.

## What It Does

- Discovers lifestyle-oriented open source projects from GitHub.
- Prioritizes projects with daily-life use cases, visual demos, and recent star activity.
- Supports Chinese and English UI/output modes.
- Translates project descriptions into Chinese with the user's OpenAI API key, while keeping repository names, commands, languages, and technical terms intact.
- Provides movie-picker-style filters for language, topic, and ranking strategy.
- Caches generated project analysis locally to avoid repeated token usage.
- Keeps the selected project highlighted while analysis is loading or displayed.
- Reads README, `package.json`, and `requirements.txt` when available.
- Generates:
  - a plain-language one-line summary
  - setup difficulty from 1 to 10
  - macOS and Windows setup requirements
  - AI DIY upgrade ideas
  - common deployment pitfalls

## Tech Stack

- Python 3.11+
- FastAPI
- Uvicorn
- httpx
- GitHub GraphQL API
- OpenAI API
- Pydantic

## Setup

```bash
cd github-diy-mentor

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`:

```text
GITHUB_TOKEN=your_github_token
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4.1-mini
```

## Run

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000
```

## Usage

Click **发现项目** with an empty search box to browse default lifestyle and productivity discoveries.

Use the top controls to customize discovery:

- **中文 / English** switches the UI and generated output language.
- **语言 / Language** filters for all, Chinese, English, or other-language projects.
- **主题 / Topic** filters by areas such as AI ideas, smart home, creative media, productivity, finance, games, and humanities.
- **排序 / Sort** switches between trending, most stars, beginner friendly, hardware projects, and software-only projects.

You can also enter a search phrase:

```text
整理衣柜
选菜
recipe
wardrobe
home automation
```

Click a project in the result list to generate the analysis and DIY mentor suggestions.

Generated analysis is cached by repository, update time, and UI language. Clicking the same project again loads from cache instead of calling OpenAI again.

## Terminal Usage

Discover projects:

```bash
curl "http://127.0.0.1:8000/api/discover?days=7&limit=5"
```

Discover with filters:

```bash
curl "http://127.0.0.1:8000/api/discover?days=7&limit=5&ui_language=zh&topic_filter=home&sort_mode=trending"
curl "http://127.0.0.1:8000/api/discover?days=30&limit=5&ui_language=en&topic_filter=productivity&sort_mode=beginner"
```

Search for a specific idea:

```bash
curl "http://127.0.0.1:8000/api/discover?days=30&limit=5&q=wardrobe"
```

Run the standalone scout script:

```bash
python scripts/scout_github_trending.py
python scripts/scout_github_trending.py wardrobe
```

## Tests

```bash
python -m pytest
```

## Notes

- `.env` is ignored by Git and should never be committed.
- `data/analysis_cache.json` is generated locally and ignored by Git.
- GitHub discovery requires `GITHUB_TOKEN`.
- AI mentor generation uses OpenAI when `OPENAI_API_KEY` is configured.
- If the OpenAI call fails, the app falls back to local DIY suggestions instead of crashing.

## Updates

### 2026-05-01 / v0.2

- Added Chinese and English mode switching for UI, analysis, and DIY mentor output.
- Added OpenAI-powered Chinese translation for GitHub project descriptions.
- Added multi-dimensional filters for language, topic, and ranking strategy.
- Added local analysis caching to reduce repeated OpenAI token usage.
- Improved the project list interaction with persistent selected-project highlighting.
- Removed the fixed Chinese summary prefix and made summaries more natural.

## License

MIT
