(function applyTheme() {
  const key = "Fluid_Color_Scheme";
  const apply = () => {
    let value = null;
    try { value = localStorage.getItem(key); } catch (_) {}
    if (value !== "light" && value !== "dark") value = matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    document.documentElement.dataset.theme = value;
  };
  apply();
  window.addEventListener("storage", (event) => { if (event.key === key) apply(); });
  matchMedia?.("(prefers-color-scheme: dark)").addEventListener?.("change", apply);
})();
