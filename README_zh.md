# GitHub DIY Mentor

[English README](README.md)

GitHub DIY Mentor 是一个本地运行的 FastAPI 小应用，用来发现 GitHub 上“好玩、实用、适合 DIY”的开源项目，并用 AI 帮普通用户生成改造建议。

这个项目的核心目标不是追最新框架，而是帮你找到能在生活里玩起来的开源项目，比如智能家居、效率工具、菜谱、文件整理、创意媒体、硬件小玩具等。

## 功能

- 从 GitHub 发现偏生活化、实用、有趣的开源项目。
- 支持中文 / English 两种界面和输出模式。
- 使用你的 OpenAI API Key 翻译英文项目简介，保留仓库名、命令、语言名和技术名。
- 提供类似“选电影”的多维筛选：
  - 语言：全部 / 中文 / 英文 / 其他
  - 主题：AI 灵感、量化金融、智能家居、创意媒体、极客游戏、效率黑客、人文探索
  - 排序：黑马榜、经典榜、新手友好、硬件项目、纯软工具
- 左侧项目卡片显示推荐理由，例如：
  - `7日 +100 stars`
  - `有截图/demo`
  - `Docker 可运行`
  - `README 较清晰`
  - `硬件项目` / `纯软工具`
- 点击项目后生成：
  - 一句话白话简介
  - 上手难度 1-10
  - macOS / Windows 运行门槛
  - AI DIY 改造建议
  - 避坑指南
  - 为什么这个项目值得看
- 本地缓存发现结果、翻译结果和 AI 分析结果，减少重复消耗 token。
- 支持收藏项目、只看收藏。
- 支持把当前列表和已生成 DIY 建议导出为 Markdown。

## 技术栈

- Python 3.11+
- FastAPI
- Uvicorn
- httpx
- GitHub GraphQL API
- OpenAI API
- Pydantic

## 安装

```bash
cd github-diy-mentor

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
```

编辑 `.env`：

```text
GITHUB_TOKEN=你的 GitHub Token
OPENAI_API_KEY=你的 OpenAI API Key
OPENAI_MODEL=gpt-4.1-mini
```

`.env` 已被 `.gitignore` 忽略，不会上传到 GitHub。

## 启动

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

浏览器打开：

```text
http://127.0.0.1:8000
```

## 使用方式

打开页面后，可以直接点击 **发现项目**，不输入搜索词也可以用。

也可以输入更具体的想法：

```text
整理衣柜
选菜
recipe
wardrobe
home automation
```

点击左侧项目卡片后，右侧会生成项目解读和 AI DIY 建议。

如果同一个项目已经生成过，应用会优先读取本地缓存，不会重复调用 OpenAI。需要重新生成时，可以点击详情页里的 **重新生成**。

## 命令行示例

发现默认项目：

```bash
curl "http://127.0.0.1:8000/api/discover?days=7&limit=5"
```

使用筛选：

```bash
curl "http://127.0.0.1:8000/api/discover?days=7&limit=5&ui_language=zh&topic_filter=home&sort_mode=trending"
curl "http://127.0.0.1:8000/api/discover?days=30&limit=5&ui_language=en&topic_filter=productivity&sort_mode=beginner"
```

搜索具体方向：

```bash
curl "http://127.0.0.1:8000/api/discover?days=30&limit=5&q=wardrobe"
```

运行独立 Scout 脚本：

```bash
python scripts/scout_github_trending.py
python scripts/scout_github_trending.py wardrobe
```

## 本地缓存

以下文件会在本地生成，并且不会提交到 Git：

```text
data/analysis_cache.json
data/discovery_cache.json
data/translation_cache.json
data/favorites.json
```

它们分别用于缓存 AI 分析、发现结果、翻译结果和收藏列表。

## 测试

```bash
python -m pytest
```

## 更新记录

### 2026-05-01 / v0.3

- 增加项目推荐理由标签。
- 增加发现结果缓存和翻译缓存。
- 增加收藏、只看收藏、Markdown 导出。
- 增加重新生成分析能力。
- 改善空结果状态，支持一键扩大搜索范围。

### 2026-05-01 / v0.2

- 增加中文 / English 切换。
- 增加 OpenAI 翻译项目简介。
- 增加语言、主题、排序三行筛选。
- 增加详情分析缓存，减少重复 token 消耗。
- 移除固定中文简介前缀，让摘要更自然。

## License

MIT
