const VALID_VIEWS = new Set(["timeline", "all", "reports", "topics", "favs"]);

export function parseRoute(search = "") {
  const params = new URLSearchParams(search);
  const date = params.get("date");
  const item = params.get("item");
  if (date && item) return { view: "detail", date, type: params.get("type") || "news", item };

  const oldView = params.get("view");
  if (oldView === "picks") return { view: "timeline" };
  if (oldView === "day") return { view: "reports", period: "day", ...(date ? { date } : {}) };
  if (oldView === "week") return { view: "reports", period: "week", ...(params.get("week") ? { week: params.get("week") } : {}) };

  const view = VALID_VIEWS.has(oldView) ? oldView : "timeline";
  if (view !== "reports") return { view, ...(view === "timeline" && params.get("tag") ? { tag: params.get("tag") } : {}) };
  const period = params.get("period") === "week" ? "week" : "day";
  return { view, period, ...(period === "week" && params.get("week") ? { week: params.get("week") } : {}), ...(period === "day" && date ? { date } : {}) };
}

export function routeUrl(route) {
  if (route.view === "detail") return `?date=${encodeURIComponent(route.date)}&type=${encodeURIComponent(route.type || "news")}&item=${encodeURIComponent(route.item)}`;
  const params = new URLSearchParams({ view: route.view || "timeline" });
  if (route.view === "timeline" && route.tag) params.set("tag", route.tag);
  if (route.view === "reports") {
    params.set("period", route.period === "week" ? "week" : "day");
    if (route.period === "week" && route.week) params.set("week", route.week);
    if (route.period !== "week" && route.date) params.set("date", route.date);
  }
  return `?${params.toString()}`;
}

export function navigate(route, { replace = false } = {}) {
  const url = routeUrl(route);
  history[replace ? "replaceState" : "pushState"]({}, "", url);
  window.dispatchEvent(new PopStateEvent("popstate"));
}
