export function createApiClient({ fetch, token }) {
  async function request(type, payload) {
    const response = await fetch("/api/newsState", { method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` }, body: JSON.stringify({ type, payload }) });
    const json = await response.json().catch(() => ({}));
    if (!response.ok || !json.success) throw new Error(json.error || `HTTP ${response.status}`);
    return json.data;
  }
  async function get(type) {
    const response = await fetch(`/api/newsState?type=${encodeURIComponent(type)}`, { headers: { Authorization: `Bearer ${token}` } });
    const json = await response.json().catch(() => ({}));
    if (!response.ok || !json.success) throw new Error(json.error || `HTTP ${response.status}`);
    return json.data;
  }
  return { postFeedback: (payload) => request("feedback", payload), postReadLater: (payload) => request("read_later", payload), postFavorite: (payload) => request("favorites", payload), get };
}
