export function getApiBase() {
  return location.protocol === "file:" ? "http://127.0.0.1:8000" : "";
}

export function apiUrl(path) {
  return `${getApiBase()}${path}`;
}

export async function readError(response) {
  const text = await response.text();
  if (!text) return response.statusText;
  try {
    const data = JSON.parse(text);
    return data.detail || response.statusText;
  } catch {
    return text;
  }
}

export async function fetchJson(path, options = {}) {
  const response = await fetch(apiUrl(path), options);
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  return response.json();
}
