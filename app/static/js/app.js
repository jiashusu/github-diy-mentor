import {fetchJson, apiUrl, readError} from "./api.js";
import {
  chipLabels,
  kindLabel,
  labels,
  localDifficulty,
  localIdeaType,
  localPlatform,
  localReason,
  localRecommendationSummary,
  repoDescription,
} from "./i18n.js";
import {createToastController} from "./toast.js";

const repoList = document.querySelector("#repoList");
const detail = document.querySelector("#detail");
const discoverButton = document.querySelector("#discover");
const favoritesToggle = document.querySelector("#favoritesToggle");
const exportButton = document.querySelector("#exportMarkdown");
const pageNav = document.querySelector("#pageNav");
const toast = createToastController(document.querySelector("#toastRegion"));

const state = {
  language: "zh",
  language_filter: "all",
  topic_filter: "all",
  sort_mode: "trending",
  repos: [],
  pages: [],
  pageIndex: -1,
  selectedName: "",
  loadingName: "",
  analysisCache: new Map(),
  favorites: new Map(),
  showFavoritesOnly: false,
  currentResult: null,
  canAppend: true,
  copyFallback: "",
};

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, char => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  }[char]));
}

function t(key) {
  return labels[state.language][key] || labels.zh[key] || key;
}

function displayedRepos() {
  if (!state.showFavoritesOnly) return state.repos;
  return state.repos.filter(repo => state.favorites.has(repo.name));
}

function renderPageNav() {
  if (!pageNav) return;
  const pageButtons = state.pages.map((_, index) => `
    <button class="page-chip ${index === state.pageIndex ? "active" : ""}" data-page-index="${index}" title="${escapeHtml(state.language === "zh" ? `第${index + 1}页` : `Page ${index + 1}`)}">
      ${index + 1}
    </button>
  `).join("");
  const addDisabled = discoverButton.disabled || state.showFavoritesOnly || !state.canAppend;
  pageNav.innerHTML = `
    <div class="page-group">${pageButtons || `<span class="page-hint">${escapeHtml(t("waiting"))}</span>`}</div>
    <button id="appendPage" class="secondary page-add" ${addDisabled ? "disabled" : ""}>+ ${escapeHtml(t("newPage"))}</button>
  `;
  pageNav.querySelectorAll("[data-page-index]").forEach(button => {
    button.addEventListener("click", () => showPage(Number(button.dataset.pageIndex)));
  });
  pageNav.querySelector("#appendPage")?.addEventListener("click", appendPage);
}

function renderRepos(repos = displayedRepos()) {
  if (!repos.length) {
    repoList.innerHTML = `
      <div class="empty">
        ${escapeHtml(t("noResults"))}
        <div class="empty-actions">
          <button class="secondary" id="broadenDays">${escapeHtml(t("broaden30"))}</button>
          <button class="secondary" id="resetTopic">${escapeHtml(t("resetTopic"))}</button>
        </div>
      </div>`;
    document.querySelector("#broadenDays")?.addEventListener("click", () => {
      document.querySelector("#days").value = 30;
      discover();
    });
    document.querySelector("#resetTopic")?.addEventListener("click", () => {
      state.topic_filter = "all";
      document.querySelectorAll('[data-filter="topic_filter"] .chip').forEach(chip => {
        chip.classList.toggle("active", chip.dataset.value === "all");
      });
      discover();
    });
    renderPageNav();
    return;
  }

  repoList.innerHTML = repos.map((repo, index) => `
    <button class="repo ${repo.name === state.selectedName ? "active" : ""} ${repo.name === state.loadingName ? "loading" : ""}" data-index="${index}">
      <strong>${state.favorites.has(repo.name) ? "★ " : ""}${escapeHtml(repo.name)}</strong>
      <p>${escapeHtml(repoDescription(repo, state.language))}</p>
      <span class="meta">
        <span>★ ${repo.stars_total}</span>
        <span>${state.language === "zh" ? "7日" : "7d"} +${repo.stars_last_7d_estimate}</span>
        <span>${escapeHtml(repo.language || "Unknown")}</span>
        <span>${escapeHtml(t("beginner"))} ${repo.beginner_score}/10</span>
        <span>${escapeHtml(kindLabel(repo.project_kind, state.language))}</span>
      </span>
      <span class="tag-row">
        ${(repo.recommendation_reasons || []).slice(0, 4).map(reason => `<span class="tag">${escapeHtml(localReason(reason, state.language))}</span>`).join("")}
      </span>
    </button>
  `).join("");

  repoList.querySelectorAll(".repo").forEach(button => {
    button.addEventListener("click", () => analyzeRepo(repos[Number(button.dataset.index)]));
  });
  renderPageNav();
}

function showEmptyDetail() {
  detail.innerHTML = `<div class="empty">${escapeHtml(t("waiting"))}</div>`;
}

function showPage(index) {
  if (index < 0 || index >= state.pages.length) return;
  state.pageIndex = index;
  state.repos = state.pages[index];
  state.selectedName = "";
  state.loadingName = "";
  state.currentResult = null;
  state.copyFallback = "";
  showEmptyDetail();
  renderRepos();
}

function allSeenNames() {
  return Array.from(new Set(state.pages.flat().map(repo => repo.name)));
}

async function discover(options = {}) {
  const appendPage = options.appendPage || false;
  discoverButton.disabled = true;
  state.selectedName = "";
  state.loadingName = "";
  state.currentResult = null;
  state.copyFallback = "";
  if (!appendPage) {
    state.repos = [];
    state.pages = [];
    state.pageIndex = -1;
    state.canAppend = true;
  }

  repoList.innerHTML = `<div class="empty">${escapeHtml(t("discovering"))}</div>`;
  showEmptyDetail();
  renderPageNav();

  try {
    const params = new URLSearchParams({
      days: document.querySelector("#days").value,
      limit: document.querySelector("#limit").value,
      ui_language: state.language,
      language_filter: state.language_filter,
      topic_filter: state.topic_filter,
      sort_mode: state.sort_mode,
    });
    const rawQuery = document.querySelector("#query").value.trim();
    if (rawQuery) params.set("q", rawQuery);
    if (appendPage) {
      const excludeNames = allSeenNames();
      if (excludeNames.length) params.set("exclude", excludeNames.join(","));
    }
    const repos = await fetchJson(`/api/discover?${params.toString()}`);
    if (appendPage) {
      if (!repos.length) {
        state.canAppend = false;
        state.repos = state.pages[state.pageIndex] || state.repos;
        renderRepos();
        toast.show(t("noMoreBatch"), "info");
        return;
      }
      state.pages.push(repos);
      state.pageIndex = state.pages.length - 1;
    } else {
      state.pages = [repos];
      state.pageIndex = 0;
    }
    state.repos = repos;
    state.showFavoritesOnly = false;
    favoritesToggle.textContent = t("favoritesOnly");
    renderRepos();
  } catch (error) {
    repoList.innerHTML = `<div class="empty">${escapeHtml(t("failed") + error.message)}</div>`;
  } finally {
    discoverButton.disabled = false;
    renderPageNav();
  }
}

async function appendPage() {
  if (discoverButton.disabled || state.showFavoritesOnly || !state.canAppend) return;
  await discover({appendPage: true});
}

async function analyzeRepo(repo, forceRefresh = false) {
  state.selectedName = repo.name;
  state.loadingName = repo.name;
  state.copyFallback = "";
  renderRepos();
  const cacheKey = `${repo.name}|${repo.pushed_at || ""}|${state.language}`;
  if (!forceRefresh && state.analysisCache.has(cacheKey)) {
    state.loadingName = "";
    renderDetail(state.analysisCache.get(cacheKey));
    renderRepos();
    return;
  }

  detail.innerHTML = `<h2>${escapeHtml(repo.name)}</h2><p class="status">${escapeHtml(t("analyzing"))}</p>`;
  try {
    const result = await fetchJson(`/api/full-analysis?force_refresh=${forceRefresh ? "true" : "false"}`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({repo, ui_language: state.language}),
    });
    state.analysisCache.set(cacheKey, result);
    renderDetail(result);
  } catch (error) {
    detail.innerHTML = `<div class="empty">${escapeHtml(t("analyzeFailed") + error.message)}</div>`;
  } finally {
    state.loadingName = "";
    renderRepos();
  }
}

function renderDetail(result) {
  state.currentResult = result;
  const {repo, analysis, mentor} = result;
  detail.innerHTML = `
    <h2>${escapeHtml(repo.name)}</h2>
    <p><a href="${escapeHtml(repo.url)}" target="_blank" rel="noreferrer">${escapeHtml(t("openGithub"))}</a>${result.cached ? ` · <span class="badge">${escapeHtml(t("cached"))}</span>` : ""}</p>
    <div class="detail-actions">
      <button class="secondary" id="favoriteDetail">${escapeHtml(state.favorites.has(repo.name) ? t("unfavorite") : t("favorite"))}</button>
      <button class="secondary" id="copyMarkdown">${escapeHtml(t("copyMarkdown"))}</button>
      <button class="secondary" id="regenerate">${escapeHtml(t("regenerate"))}</button>
    </div>
    ${state.copyFallback ? `
      <div class="copy-fallback">
        <strong>${escapeHtml(state.language === "zh" ? "复制失败时的备选文本" : "Fallback text for manual copy")}</strong>
        <textarea id="copyFallbackText" readonly>${escapeHtml(state.copyFallback)}</textarea>
        <div class="status">${escapeHtml(state.language === "zh" ? "已经选中下面的文本框，你可以直接按 Cmd/Ctrl+C。" : "The text area below is selected. Press Cmd/Ctrl+C.")}</div>
      </div>
    ` : ""}
    <h3>${escapeHtml(t("why"))}</h3>
    <p>${escapeHtml(localRecommendationSummary(result, state.language))}</p>
    <div class="tag-row">
      ${(repo.recommendation_reasons || []).map(reason => `<span class="tag">${escapeHtml(localReason(reason, state.language))}</span>`).join("")}
      <span class="tag">${escapeHtml(t("beginner"))} ${repo.beginner_score}/10</span>
      <span class="tag">${escapeHtml(t("kind"))}: ${escapeHtml(kindLabel(repo.project_kind, state.language))}</span>
    </div>
    <h3>${escapeHtml(t("summary"))}</h3>
    <p>${escapeHtml(analysis.plain_summary)}</p>
    <h3>${escapeHtml(t("difficulty"))}</h3>
    <p><span class="badge">${analysis.difficulty_score}/10</span></p>
    <h3>${escapeHtml(t("macos"))}</h3>
    <ul>${analysis.macos_requirements.map(item => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
    <h3>${escapeHtml(t("windows"))}</h3>
    <ul>${analysis.windows_requirements.map(item => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
    <h3>${escapeHtml(t("angle"))}</h3>
    <p>${escapeHtml(mentor.overall_angle)}</p>
    ${mentor.ideas.map(idea => `
      <div class="idea">
        <span class="badge">${escapeHtml(localIdeaType(idea.type, state.language))} · ${escapeHtml(localDifficulty(idea.difficulty, state.language))}</span>
        <h3>${escapeHtml(idea.title)}</h3>
        <p>${escapeHtml(idea.direction)}</p>
        <p><strong>${escapeHtml(t("forWhom"))}</strong>${escapeHtml(idea.for_whom)}</p>
        <ul>${idea.minimum_steps.map(step => `<li>${escapeHtml(step)}</li>`).join("")}</ul>
        <p><strong>${escapeHtml(t("capability"))}</strong>${escapeHtml(idea.ai_capability)}</p>
        <p><strong>${escapeHtml(t("useful"))}</strong>${escapeHtml(idea.why_this_is_useful)}</p>
      </div>
    `).join("")}
    <h3>${escapeHtml(t("pitfalls"))}</h3>
    <ul>${mentor.pitfalls.map(pitfall => `<li><strong>${escapeHtml(localPlatform(pitfall.platform, state.language))}${state.language === "en" ? ":" : "："}</strong>${escapeHtml(pitfall.symptom)}${state.language === "en" ? "; " : "；"}${escapeHtml(pitfall.fix)}</li>`).join("")}</ul>
  `;
  document.querySelector("#favoriteDetail").addEventListener("click", () => toggleFavorite(repo));
  document.querySelector("#copyMarkdown").addEventListener("click", copyCurrentMarkdown);
  document.querySelector("#regenerate").addEventListener("click", () => analyzeRepo(repo, true));
  if (state.copyFallback) {
    window.setTimeout(() => {
      const fallback = document.querySelector("#copyFallbackText");
      fallback?.focus();
      fallback?.select();
    }, 0);
  }
}

async function loadFavorites() {
  try {
    const favorites = await fetchJson("/api/favorites");
    state.favorites = new Map(favorites.map(repo => [repo.name, repo]));
    if (state.repos.length || state.showFavoritesOnly) renderRepos();
  } catch {}
}

async function toggleFavorite(repo) {
  const isFavorite = state.favorites.has(repo.name);
  const options = isFavorite
    ? {method: "DELETE"}
    : {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({repo})};
  const response = await fetch(apiUrl(isFavorite ? `/api/favorites/${encodeURIComponent(repo.name)}` : "/api/favorites"), options);
  if (!response.ok) throw new Error(await readError(response));
  const favorites = await response.json();
  state.favorites = new Map(favorites.map(item => [item.name, item]));
  toast.show(isFavorite ? t("removed") : t("saved"), isFavorite ? "info" : "success");
  if (state.currentResult?.repo?.name === repo.name) renderDetail(state.currentResult);
  renderRepos();
}

async function copyCurrentMarkdown() {
  if (!state.currentResult) return;
  try {
    const markdown = state.currentResult.markdown_export || "";
    await writeClipboard(markdown);
    state.copyFallback = "";
    const button = document.querySelector("#copyMarkdown");
    if (button) {
      const original = button.textContent;
      button.textContent = t("copied");
      window.setTimeout(() => { button.textContent = original; }, 1200);
    }
    toast.show(t("copied"), "success");
  } catch (error) {
    state.copyFallback = state.currentResult.markdown_export || "";
    renderDetail(state.currentResult);
    toast.show(state.language === "zh" ? "已选中文本，按 Cmd/Ctrl+C 复制" : "Text selected, press Cmd/Ctrl+C", "info");
  }
}

async function writeClipboard(text) {
  if (navigator.clipboard?.writeText && document.hasFocus()) {
    await navigator.clipboard.writeText(text);
    return;
  }
  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "true");
  textarea.style.position = "fixed";
  textarea.style.opacity = "0";
  textarea.style.left = "-9999px";
  document.body.appendChild(textarea);
  textarea.focus();
  textarea.select();
  const success = document.execCommand("copy");
  textarea.remove();
  if (!success) {
    throw new Error("Clipboard copy failed");
  }
}

async function exportMarkdown() {
  try {
    const analyses = Array.from(state.analysisCache.values());
    const result = await fetchJson("/api/export/markdown", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({repos: state.repos, analyses, ui_language: state.language}),
    });
    const blob = new Blob([result.markdown], {type: "text/markdown;charset=utf-8"});
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "github-diy-mentor-export.md";
    link.click();
    URL.revokeObjectURL(url);
    toast.show(t("exported"), "success");
  } catch (error) {
    toast.show(error.message || t("exported"), "error");
  }
}

function applyLanguage() {
  document.querySelector("h1").textContent = t("title");
  document.querySelectorAll("[data-i18n]").forEach(node => {
    node.textContent = t(node.dataset.i18n);
  });
  document.querySelectorAll(".filter-row").forEach(row => {
    const group = row.dataset.filter;
    row.querySelectorAll(".chip").forEach(chip => {
      chip.textContent = chipLabels[state.language][group][chip.dataset.value];
    });
  });
  if (!state.repos.length) {
    repoList.innerHTML = `<div class="empty">${escapeHtml(t("start"))}</div>`;
  }
  favoritesToggle.textContent = state.showFavoritesOnly ? t("allResults") : t("favoritesOnly");
  renderPageNav();
}

discoverButton.addEventListener("click", () => discover());
favoritesToggle.addEventListener("click", () => {
  state.showFavoritesOnly = !state.showFavoritesOnly;
  favoritesToggle.textContent = state.showFavoritesOnly ? t("allResults") : t("favoritesOnly");
  renderRepos();
});
exportButton.addEventListener("click", exportMarkdown);
document.querySelector("#query").addEventListener("keydown", event => {
  if (event.key === "Enter") discover();
});
document.querySelectorAll(".filter-row").forEach(row => {
  const key = row.dataset.filter;
  row.querySelectorAll(".chip").forEach(chip => {
    chip.addEventListener("click", () => {
      state[key] = chip.dataset.value;
      row.querySelectorAll(".chip").forEach(item => item.classList.remove("active"));
      chip.classList.add("active");
      discover();
    });
  });
});
document.querySelectorAll(".lang-toggle").forEach(button => {
  button.addEventListener("click", event => {
    event.preventDefault();
    state.language = button.dataset.lang;
    document.querySelectorAll(".lang-toggle").forEach(item => item.classList.remove("active"));
    button.classList.add("active");
    applyLanguage();
    if (state.repos.length) renderRepos();
    if (state.selectedName) {
      const repo = state.repos.find(item => item.name === state.selectedName);
      if (repo) {
        analyzeRepo(repo);
        return;
      }
    }
    showEmptyDetail();
  });
});

applyLanguage();
loadFavorites();
renderPageNav();
