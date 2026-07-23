export function createApiClient({ fetch }) {
  async function request(type, payload) {
    const response = await fetch("/api/newsState", { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ type, payload }) });
    const json = await response.json().catch(() => ({}));
    if (!response.ok || !json.success) throw new Error(json.error || `HTTP ${response.status}`);
    return json.data;
  }
  async function get(type) {
    const response = await fetch(`/api/newsState?type=${encodeURIComponent(type)}`, { credentials: "same-origin" });
    const json = await response.json().catch(() => ({}));
    if (!response.ok || !json.success) throw new Error(json.error || `HTTP ${response.status}`);
    return json.data;
  }
  return {
    postFeedback: (payload) => request("feedback", payload),
    postReadLater: (payload) => request("read_later", payload),
    postFavorite: (payload) => request("favorites", payload),
    postMiss: (payload) => request("misses", payload),
    get,
  };
}
