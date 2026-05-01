export const labels = {
  zh: {
    title: "GitHub 趣事发现器 & AI DIY 导师",
    search: "搜索",
    days: "天数",
    limit: "数量",
    discover: "发现项目",
    language: "语言",
    topic: "主题",
    sort: "排序",
    start: "点击“发现项目”开始。需要先在 `.env` 配置 `GITHUB_TOKEN`。",
    waiting: "等待选择项目。",
    discovering: "正在从 GitHub 捞有意思的项目...",
    noResults: "没有找到合适项目。可以扩大天数或稍后再试。",
    failed: "发现失败：",
    analyzing: "正在生成解读和 DIY 建议...",
    analyzeFailed: "分析失败：",
    openGithub: "打开 GitHub",
    summary: "一句话白话简介",
    difficulty: "上手难度",
    macos: "macOS 门槛",
    windows: "Windows 门槛",
    angle: "AI 改造总方向",
    pitfalls: "避坑指南",
    capability: "AI 能力：",
    useful: "为什么有用：",
    forWhom: "适合：",
    cached: "已从缓存加载",
    favoritesOnly: "只看收藏",
    allResults: "看全部",
    export: "导出",
    favorite: "收藏",
    unfavorite: "取消收藏",
    regenerate: "重新生成",
    copyMarkdown: "复制 DIY 方案",
    why: "为什么值得看",
    beginner: "新手分",
    kind: "类型",
    copied: "已复制",
    saved: "已收藏",
    removed: "已取消收藏",
    exported: "导出成功",
    broaden30: "扩大到 30 天",
    resetTopic: "切回全部主题",
    page: "页",
    newPage: "新一页",
    noMoreBatch: "没有更多新项目了"
  },
  en: {
    title: "GitHub Fun Finder & AI DIY Mentor",
    search: "Search",
    days: "Days",
    limit: "Limit",
    discover: "Discover",
    language: "Language",
    topic: "Topic",
    sort: "Sort",
    start: "Click Discover to start. Configure GITHUB_TOKEN in `.env` first.",
    waiting: "Select a project to see analysis and AI DIY suggestions.",
    discovering: "Finding interesting GitHub projects...",
    noResults: "No matching projects found. Try more days or a broader filter.",
    failed: "Discovery failed: ",
    analyzing: "Generating analysis and DIY suggestions...",
    analyzeFailed: "Analysis failed: ",
    openGithub: "Open GitHub",
    summary: "Plain-language Summary",
    difficulty: "Setup Difficulty",
    macos: "macOS Requirements",
    windows: "Windows Requirements",
    angle: "AI Upgrade Direction",
    pitfalls: "Pitfalls",
    capability: "AI capability: ",
    useful: "Why useful: ",
    forWhom: "For: ",
    cached: "Loaded from cache",
    favoritesOnly: "Favorites",
    allResults: "All Results",
    export: "Export",
    favorite: "Favorite",
    unfavorite: "Unfavorite",
    regenerate: "Regenerate",
    copyMarkdown: "Copy DIY Plan",
    why: "Why It Is Worth Checking",
    beginner: "Beginner",
    kind: "Kind",
    copied: "Copied",
    saved: "Saved",
    removed: "Removed",
    exported: "Exported",
    broaden30: "Expand to 30 days",
    resetTopic: "Reset topic",
    page: "Page",
    newPage: "New page",
    noMoreBatch: "No more new projects"
  }
};

export const chipLabels = {
  zh: {
    language_filter: {all: "全部", zh: "中文", en: "英文", other: "其他"},
    topic_filter: {all: "全部", ai: "AI 灵感", finance: "量化金融", home: "智能家居", media: "创意媒体", game: "极客游戏", productivity: "效率黑客", humanities: "人文探索"},
    sort_mode: {trending: "黑马榜", stars: "经典榜", beginner: "新手友好", hardware: "硬件项目", software: "纯软工具"}
  },
  en: {
    language_filter: {all: "All", zh: "Chinese", en: "English", other: "Other"},
    topic_filter: {all: "All", ai: "AI Ideas", finance: "Quant Finance", home: "Smart Home", media: "Creative Media", game: "Geek Games", productivity: "Productivity", humanities: "Humanities"},
    sort_mode: {trending: "Trending", stars: "Most Stars", beginner: "Beginner Friendly", hardware: "Hardware", software: "Software Only"}
  }
};

export function repoDescription(repo, language) {
  if (language === "zh") return repo.description_zh || repo.description || "暂无简介";
  return repo.description_en || repo.description || "No description";
}

export function localReason(reason, language) {
  if (language === "zh") return reason;
  return String(reason)
    .replace("7日", "7d")
    .replace("有截图/demo", "Screenshots/demo")
    .replace("Docker 可运行", "Docker runnable")
    .replace("新手友好", "Beginner friendly")
    .replace("硬件项目", "Hardware")
    .replace("纯软工具", "Software only")
    .replace("软硬结合", "Hardware + software")
    .replace("README 较清晰", "Clear README");
}

export function localIdeaType(value, language) {
  const map = {
    zh: {"Lazy Plan": "懒人方案", "AI Upgrade": "AI增强版", "懒人方案": "懒人方案", "AI增强版": "AI增强版"},
    en: {"Lazy Plan": "Lazy Plan", "AI Upgrade": "AI Upgrade", "懒人方案": "Lazy Plan", "AI增强版": "AI Upgrade"}
  };
  return map[language][value] || value;
}

export function localDifficulty(value, language) {
  const map = {
    zh: {Low: "低", Medium: "中", High: "高", "低": "低", "中": "中", "高": "高"},
    en: {Low: "Low", Medium: "Medium", High: "High", "低": "Low", "中": "Medium", "高": "High"}
  };
  return map[language][value] || value;
}

export function localPlatform(value, language) {
  const map = {
    zh: {General: "通用", "通用": "通用", macOS: "macOS", Windows: "Windows"},
    en: {General: "General", "通用": "General", macOS: "macOS", Windows: "Windows"}
  };
  return map[language][value] || value;
}

export function localRecommendationSummary(result, language) {
  const reasons = (result.repo.recommendation_reasons || []).slice(0, 4).map(reason => localReason(reason, language));
  if (!reasons.length) return result.recommendation_summary || "";
  if (language === "en") return `Worth checking because: ${reasons.join(", ")}.`;
  return `值得看，因为：${reasons.join("、")}。`;
}

export function kindLabel(kind, language) {
  const zh = {software: "纯软", hardware: "硬件", mixed: "软硬结合", unknown: "未知"};
  const en = {software: "Software", hardware: "Hardware", mixed: "Mixed", unknown: "Unknown"};
  return (language === "zh" ? zh : en)[kind] || kind;
}
