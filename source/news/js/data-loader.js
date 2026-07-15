const pending = new Map();
const DATE_ID = /^(\d{4})-(\d{2})-(\d{2})$/;
const WEEK_ID = /^\d{4}-W(?:0[1-9]|[1-4]\d|5[0-3])$/;

function validDateId(value) {
  const match = DATE_ID.exec(String(value || ""));
  if (!match) return false;
  const [, year, month, day] = match;
  const parsed = new Date(Date.UTC(Number(year), Number(month) - 1, Number(day)));
  return parsed.getUTCFullYear() === Number(year)
    && parsed.getUTCMonth() === Number(month) - 1
    && parsed.getUTCDate() === Number(day);
}

function requireDateId(date) {
  if (!validDateId(date)) throw new Error("无效日报日期");
}

function requireWeekId(week) {
  if (!WEEK_ID.test(String(week || ""))) throw new Error("无效周报编号");
}

export function loadScript(src, predicate = () => false) {
  if (predicate()) return Promise.resolve();
  if (pending.has(src)) return pending.get(src);
  const promise = new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = src;
    script.onload = resolve;
    script.onerror = () => reject(new Error(`无法加载 ${src}`));
    document.head.appendChild(script);
  }).finally(() => pending.delete(src));
  pending.set(src, promise);
  return promise;
}

export async function daily(date) {
  requireDateId(date);
  await loadScript(`data/daily/${date}.js`, () => Boolean(window.NEWS_DATA?.[date]));
  return window.NEWS_DATA?.[date] || null;
}

export async function weeklyManifest() {
  await loadScript("data/weekly/manifest.js", () => Array.isArray(window.WEEKLY_MANIFEST));
  return window.WEEKLY_MANIFEST || [];
}

export async function weekly(week) {
  requireWeekId(week);
  await loadScript(`data/weekly/${week}.js`, () => Boolean(window.WEEKLY_DATA?.[week]));
  return window.WEEKLY_DATA?.[week] || null;
}

export async function allManifest() {
  await loadScript("data/all/manifest.js", () => Array.isArray(window.ALL_MANIFEST));
  return window.ALL_MANIFEST || [];
}

export async function allDay(date) {
  requireDateId(date);
  await loadScript(`data/all/${date}.js`, () => Boolean(window.NEWS_ALL?.[date]));
  return window.NEWS_ALL?.[date] || null;
}

export async function index() {
  await loadScript("data/search_index.js", () => Array.isArray(window.NEWS_INDEX));
  return window.NEWS_INDEX || [];
}

export async function events() {
  const response = await fetch("data/events.json");
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

export const browserDataApi = { daily, weeklyManifest, weekly, allManifest, allDay, index, events };
