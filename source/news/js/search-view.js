import { escapeHtml } from "./reports.js";
import { routeUrl } from "./router.js";

export function installSearch({ input, results, dataApi, trackPromise }) {
  const search = () => trackPromise((async () => {
    const query = input.value.trim().toLowerCase(); if (!query) { results.innerHTML = ""; results.classList.remove("open"); return; }
    const rows = (await dataApi.index()).filter((row) => `${row[4] || ""} ${row[5] || ""}`.toLowerCase().includes(query)).slice(0, 20);
    results.innerHTML = rows.length ? rows.map((row) => { const type = row[2] === "deep" ? "deep" : row[2] === "paper" ? "paper" : "news"; return `<a class="sr" href="${routeUrl({ view: "detail", date: row[0], type, item: row[1] })}" data-route>${escapeHtml(row[0])} · ${escapeHtml(row[4])}</a>`; }).join("") : '<p class="sr none">没有匹配结果</p>';
    results.classList.add("open");
  })());
  input.addEventListener("input", search); input.addEventListener("focus", search);
}
