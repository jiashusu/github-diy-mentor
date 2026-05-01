const DEFAULT_DURATION = 2200;

export function createToastController(container) {
  if (!container) {
    return {
      show() {},
      clear() {},
    };
  }

  function show(message, type = "success", duration = DEFAULT_DURATION) {
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    requestAnimationFrame(() => toast.classList.add("visible"));

    window.setTimeout(() => {
      toast.classList.remove("visible");
      window.setTimeout(() => toast.remove(), 180);
    }, duration);
  }

  function clear() {
    container.innerHTML = "";
  }

  return {show, clear};
}
