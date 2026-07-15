export function updateNavigation(root, activeView) {
  root.querySelectorAll("[data-view]").forEach((link) => {
    if (link.dataset.view === activeView) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  });
}

export function announce(message, root = document) {
  const live = root.getElementById("liveStatus");
  if (live) live.textContent = message || "";
}
