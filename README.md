# GitHub DIY Mentor

GitHub DIY Mentor is a small FastAPI web app that finds practical, playful GitHub projects and explains how ordinary users can improve them with AI.

This is the first raw version of the project: simple local UI, GitHub discovery, README/dependency analysis, and AI-generated DIY upgrade ideas.

## What It Does

- Discovers lifestyle-oriented open source projects from GitHub.
- Prioritizes projects with daily-life use cases, visual demos, and recent star activity.
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

You can also enter a search phrase, for example:

```text
整理衣柜
选菜
recipe
wardrobe
home automation
```

Click a project in the result list to generate the analysis and DIY mentor suggestions.

## Terminal Usage

Discover projects:

```bash
curl "http://127.0.0.1:8000/api/discover?days=7&limit=5"
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
- GitHub discovery requires `GITHUB_TOKEN`.
- AI mentor generation uses OpenAI when `OPENAI_API_KEY` is configured.
- If the OpenAI call fails, the app falls back to local DIY suggestions instead of crashing.

## License

MIT
