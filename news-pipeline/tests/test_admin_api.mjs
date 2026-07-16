import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const github = require("../../api/_github.js");
const adminArticles = require("../../api/adminArticles.js");

function jsonResponse(data, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    text: async () => JSON.stringify(data)
  };
}

function mockResponse() {
  return {
    statusCode: 200,
    body: null,
    headers: {},
    setHeader(name, value) { this.headers[name.toLowerCase()] = value; },
    status(code) { this.statusCode = code; return this; },
    json(body) { this.body = body; return this; },
    end() { return this; }
  };
}

function withRepoEnv(fn) {
  const before = { ...process.env };
  Object.assign(process.env, {
    ADMIN_TOKEN: "admin-secret",
    GITHUB_TOKEN: "github-secret",
    GITHUB_OWNER: "owner",
    GITHUB_REPO: "repo",
    GITHUB_BRANCH: "main"
  });
  return Promise.resolve(fn()).finally(() => {
    process.env = before;
  });
}

test("admin session is signed, expires, and never contains the admin token", () => {
  const now = Date.UTC(2026, 6, 17, 0, 0, 0);
  const value = github.createAdminSession("admin-secret", now);
  assert.doesNotMatch(value, /admin-secret/);
  assert.equal(github.verifyAdminSession(value, "admin-secret", now + 60_000), true);
  assert.equal(github.verifyAdminSession(value, "admin-secret", now + 9 * 60 * 60_000), false);
});

test("personal-session authentication accepts a signed cookie without granting bearer admin access", async () => {
  await withRepoEnv(() => {
    const now = Date.now();
    const session = github.createAdminSession("admin-secret", now);
    const req = { headers: { cookie: `aoiblog_admin_session=${session}` } };
    assert.doesNotThrow(() => github.requireAdminSession(req, now));
    assert.throws(() => github.requireAdmin(req), (error) => error.status === 401);
  });
});

test("admin frontend does not persist the bearer token in browser storage", async () => {
  const source = await readFile(new URL("../../source/admin/index.html", import.meta.url), "utf8");
  assert.doesNotMatch(source, /localStorage\.(?:getItem|setItem)\(['"]aoiblog_admin_token/);
  assert.match(source, /localStorage\.removeItem\(['"]aoiblog_admin_token/);
});

test("news frontend no longer reads or sends the bearer token", async () => {
  const app = await readFile(new URL("../../source/news/js/app.js", import.meta.url), "utf8");
  const client = await readFile(new URL("../../source/news/js/api-client.js", import.meta.url), "utf8");
  const publicScript = await readFile(new URL("../../source/js/twikoo-legacy-path.js", import.meta.url), "utf8");
  assert.doesNotMatch(app, /localStorage\.(?:getItem|setItem)\(['"]aoiblog_admin_token/);
  assert.match(app, /localStorage\.removeItem\(['"]aoiblog_admin_token/);
  assert.match(publicScript, /localStorage\.removeItem\(['"]aoiblog_admin_token/);
  assert.ok(app.indexOf('removeItem("aoiblog_admin_token")') < app.indexOf("resolvePersonalSession(window.fetch.bind(window)"));
  assert.doesNotMatch(client, /Authorization/);
  assert.match(client, /credentials:\s*["']same-origin["']/);
});

test("news session detection falls back when the session endpoint hangs", async () => {
  const { resolvePersonalSession } = await import("../../source/news/js/app.js");
  const personal = await resolvePersonalSession(
    () => new Promise(() => {}),
    (callback) => { callback(); return 1; },
    () => {}
  );
  assert.equal(personal, false);
});

test("shipped source files contain no Unicode replacement characters", async () => {
  const paths = [
    "../../source/js/aoiblog-home.js",
    "../../source/admin/index.html",
    "../../source/news/js/app.js"
  ];
  for (const path of paths) {
    const source = await readFile(new URL(path, import.meta.url), "utf8");
    assert.doesNotMatch(source, /\uFFFD/, `${path} contains broken text encoding`);
  }
});

test("write-enabled workflow pins actions and Python packages immutably", async () => {
  const workflow = await readFile(new URL("../../.github/workflows/daily-news.yml", import.meta.url), "utf8");
  const requirements = await readFile(new URL("../requirements.txt", import.meta.url), "utf8");
  assert.match(workflow, /actions\/checkout@[a-f0-9]{40}/);
  assert.match(workflow, /actions\/setup-python@[a-f0-9]{40}/);
  assert.doesNotMatch(workflow, /uses:\s+actions\/(?:checkout|setup-python)@v\d/);
  const packageLines = requirements.split(/\r?\n/).filter((line) => line && !/^\s*[#-]/.test(line));
  assert.ok(packageLines.length > 4, "transitive dependencies must be locked");
  assert.ok(packageLines.every((line) => /==[^\s\\]+/.test(line) || /\/[^/]+-\d+(?:\.\d+)+-[^/]+\.whl/.test(line)), "every dependency must use an exact version or a versioned wheel");
  assert.match(requirements, /--hash=sha256:/);
  assert.match(requirements, /news-pipeline\/vendor\/sgmllib3k-1\.0\.0-py3-none-any\.whl/);
  assert.doesNotMatch(requirements, /^sgmllib3k==/m);
});

test("atomic multi-file update creates one commit and advances the branch once", async () => {
  await withRepoEnv(async () => {
    const calls = [];
    const originalFetch = globalThis.fetch;
    globalThis.fetch = async (url, options = {}) => {
      const method = options.method || "GET";
      const body = options.body ? JSON.parse(options.body) : null;
      calls.push({ url: String(url), method, body });
      if (String(url).endsWith("/git/ref/heads/main")) return jsonResponse({ object: { sha: "head-sha" } });
      if (String(url).endsWith("/git/commits/head-sha")) return jsonResponse({ tree: { sha: "base-tree" } });
      if (String(url).endsWith("/git/blobs")) return jsonResponse({ sha: `blob-${calls.filter((call) => call.url.endsWith("/git/blobs")).length}` }, 201);
      if (String(url).endsWith("/git/trees")) return jsonResponse({ sha: "next-tree" }, 201);
      if (String(url).endsWith("/git/commits")) return jsonResponse({ sha: "next-commit" }, 201);
      if (String(url).endsWith("/git/refs/heads/main")) return jsonResponse({ object: { sha: "next-commit" } });
      throw new Error(`Unexpected request: ${method} ${url}`);
    };
    try {
      await github.putTextFilesAtomic([
        { path: "_config.yml", content: "title: next" },
        { path: "_config.fluid.yml", content: "footer: next" }
      ], "update settings");
    } finally {
      globalThis.fetch = originalFetch;
    }

    const commits = calls.filter((call) => call.url.endsWith("/git/commits") && call.method === "POST");
    const updates = calls.filter((call) => call.url.endsWith("/git/refs/heads/main") && call.method === "PATCH");
    assert.equal(commits.length, 1);
    assert.equal(updates.length, 1);
    assert.deepEqual(commits[0].body.parents, ["head-sha"]);
    assert.equal(calls.find((call) => call.url.endsWith("/git/trees") && call.method === "POST").body.tree.length, 2);
  });
});

test("atomic multi-file update rejects stale source blobs before creating a commit", async () => {
  await withRepoEnv(async () => {
    const calls = [];
    const originalFetch = globalThis.fetch;
    globalThis.fetch = async (url, options = {}) => {
      calls.push({ url: String(url), method: options.method || "GET" });
      if (String(url).endsWith("/git/ref/heads/main")) return jsonResponse({ object: { sha: "head-sha" } });
      if (String(url).endsWith("/git/commits/head-sha")) return jsonResponse({ tree: { sha: "base-tree" } });
      if (String(url).includes("/git/trees/base-tree?recursive=1")) {
        return jsonResponse({ tree: [{ path: "_config.yml", type: "blob", sha: "newer-sha" }] });
      }
      return jsonResponse({ sha: "unexpected" }, 201);
    };
    try {
      await assert.rejects(
        github.putTextFilesAtomic(
          [{ path: "_config.yml", content: "title: stale" }],
          "update settings",
          { expectedFiles: [{ path: "_config.yml", sha: "editor-sha" }] }
        ),
        (error) => error.status === 409
      );
    } finally {
      globalThis.fetch = originalFetch;
    }
    assert.equal(calls.some((call) => call.url.endsWith("/git/commits") && call.method === "POST"), false);
  });
});

test("article save rejects a stale editor SHA without writing", async () => {
  await withRepoEnv(async () => {
    const originalFetch = globalThis.fetch;
    let writes = 0;
    globalThis.fetch = async (url, options = {}) => {
      const path = String(url);
      if ((options.method || "GET") === "PUT") { writes += 1; return jsonResponse({ content: { sha: "saved" } }); }
      if (path.includes("category-covers.json")) return jsonResponse({ sha: "covers", content: Buffer.from('{"default":"/fallback.webp"}').toString("base64") });
      if (path.includes("source/_posts/post.md")) return jsonResponse({ sha: "current-sha", content: Buffer.from('---\ntitle: "Current"\ndate: "2026-07-17"\ncategories:\n  - "技术"\n---\nCurrent body\n').toString("base64") });
      throw new Error(`Unexpected request: ${path}`);
    };
    const req = { method: "POST", headers: { authorization: "Bearer admin-secret" }, query: {}, body: { article: { filePath: "source/_posts/post.md", sha: "editor-sha", title: "Edited", date: "2026-07-17", category: "技术", content: "Edited body" } } };
    const res = mockResponse();
    try { await adminArticles(req, res); } finally { globalThis.fetch = originalFetch; }
    assert.equal(res.statusCode, 409);
    assert.equal(writes, 0);
  });
});

test("article delete rejects a stale editor SHA without deleting", async () => {
  await withRepoEnv(async () => {
    const originalFetch = globalThis.fetch;
    let deletes = 0;
    globalThis.fetch = async (url, options = {}) => {
      if ((options.method || "GET") === "DELETE") { deletes += 1; return jsonResponse({}); }
      return jsonResponse({ sha: "current-sha", content: Buffer.from("post").toString("base64") });
    };
    const req = { method: "DELETE", headers: { authorization: "Bearer admin-secret" }, query: {}, body: { filePath: "source/_posts/post.md", sha: "editor-sha" } };
    const res = mockResponse();
    try { await adminArticles(req, res); } finally { globalThis.fetch = originalFetch; }
    assert.equal(res.statusCode, 409);
    assert.equal(deletes, 0);
  });
});
