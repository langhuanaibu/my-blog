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

export function installMobileSearch(root) {
  const toggle = root.getElementById("mobileSearchToggle");
  const panel = root.getElementById("mobileSearchPanel");
  const input = root.getElementById("searchInput");
  const closeButton = root.getElementById("mobileSearchClose");
  if (!toggle || !panel || !input) return;
  const desktop = root.defaultView?.matchMedia?.("(min-width: 900px)");
  const clearDialog = () => { panel.removeAttribute("role"); panel.removeAttribute("aria-modal"); };
  const focusable = () => [...new Set(panel.querySelectorAll('input:not([disabled]),button:not([disabled]),a[href],[tabindex]:not([tabindex="-1"])'))]
    .filter((node) => {
      const style = root.defaultView?.getComputedStyle?.(node);
      return !node.disabled && !node.hidden && !node.closest("[hidden]") && style?.display !== "none" && style?.visibility !== "hidden";
    });
  const close = () => {
    panel.hidden = true;
    toggle.setAttribute("aria-expanded", "false");
    clearDialog();
    toggle.focus();
  };
  const open = () => {
    panel.hidden = false;
    toggle.setAttribute("aria-expanded", "true");
    if (!desktop?.matches) { panel.setAttribute("role", "dialog"); panel.setAttribute("aria-modal", "true"); }
    input.focus();
  };
  toggle.addEventListener("click", () => panel.hidden ? open() : close());
  closeButton?.addEventListener("click", close);
  root.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !desktop?.matches && !panel.hidden) close();
    if (event.key === "Tab" && !desktop?.matches && !panel.hidden) {
      const controls = focusable(); const first = controls[0]; const last = controls.at(-1);
      if (event.shiftKey && root.activeElement === first) { event.preventDefault(); last?.focus(); }
      else if (!event.shiftKey && root.activeElement === last) { event.preventDefault(); first?.focus(); }
      else if (!controls.includes(root.activeElement)) { event.preventDefault(); first?.focus(); }
    }
  });
  const syncDesktop = () => {
    if (desktop?.matches) { panel.hidden = false; toggle.setAttribute("aria-expanded", "false"); clearDialog(); }
    else if (toggle.getAttribute("aria-expanded") !== "true") { panel.hidden = true; clearDialog(); }
  };
  desktop?.addEventListener?.("change", syncDesktop);
  syncDesktop();
}

export function installThemeToggles(root, win) {
  root.querySelectorAll("[data-theme-toggle]").forEach((button) => button.addEventListener("click", () => {
    const next = root.documentElement.dataset.theme === "dark" ? "light" : "dark";
    root.documentElement.dataset.theme = next;
    try { win.localStorage.setItem("Fluid_Color_Scheme", next); } catch (_) {}
  }));
}
