from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.github_scout import discover_repositories  # noqa: E402


async def main() -> None:
    load_dotenv(ROOT / ".env")
    keyword = " ".join(sys.argv[1:]) or None
    repos = await discover_repositories(days=7, limit=30, keyword=keyword)
    print(json.dumps([repo.model_dump(mode="json") for repo in repos], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
