import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { marked } from "marked";
import { JSDOM } from "jsdom";

const scriptSource = await readFile(
  new URL("../source/js/aoiblog-home.js", import.meta.url),
  "utf8",
);
const postCssSource = await readFile(
  new URL("../source/css/aoiblog-post.css", import.meta.url),
  "utf8",
);
const homeCssSource = await readFile(
  new URL("../source/css/aoiblog-home.css", import.meta.url),
  "utf8",
);
const vercelConfig = JSON.parse(await readFile(
  new URL("../vercel.json", import.meta.url),
  "utf8",
));

function createPostDom(body, { desktop = false, height = 500 } = {}) {
  const dom = new JSDOM(
    `<!doctype html><html><body>${body}</body></html>`,
    {
      runScripts: "outside-only",
      url: "https://aoiblog.top/2026/07/23/example/",
    },
  );
  const { window } = dom;

  Object.defineProperty(window, "innerHeight", {
    configurable: true,
    value: height,
  });
  Object.defineProperty(window, "scrollY", {
    configurable: true,
    writable: true,
    value: 0,
  });

  window.matchMedia = (query) => ({
    matches: query.includes("min-width") ? desktop : !desktop,
    media: query,
    addEventListener() {},
    removeEventListener() {},
  });
  window.requestAnimationFrame = (callback) => {
    callback();
    return 1;
  };
  window.cancelAnimationFrame = () => {};

  const article = window.document.querySelector(".post-content");
  if (article) {
    article.getBoundingClientRect = () => ({
      top: 50 - window.scrollY,
      bottom: 1550 - window.scrollY,
      left: 0,
      right: 720,
      width: 720,
      height: 1500,
      x: 0,
      y: 50 - window.scrollY,
      toJSON() {},
    });
  }
  const markdown = window.document.querySelector(".markdown-body");
  if (markdown) {
    markdown.getBoundingClientRect = () => ({
      top: 100 - window.scrollY,
      bottom: 1200 - window.scrollY,
      left: 0,
      right: 720,
      width: 720,
      height: 1100,
      x: 0,
      y: 100 - window.scrollY,
      toJSON() {},
    });
  }

  return dom;
}

function runReadingScript(dom) {
  dom.window.eval(scriptSource);
}

function waitForDomWork(window) {
  return new Promise((resolve) => window.setTimeout(resolve, 0));
}

test("updates article progress and desktop reading state from scroll position", () => {
  const dom = createPostDom(
    `
      <div class="side-col"></div>
      <article class="post-content"><div class="markdown-body"><p>正文</p></div></article>
      <div class="side-col"></div>
    `,
    { desktop: true },
  );
  const { window } = dom;

  runReadingScript(dom);
  window.scrollY = 400;
  window.dispatchEvent(new window.Event("scroll"));

  const progress = window.document.querySelector(".aoi-reading-progress__bar");
  assert.ok(progress, "文章页应创建阅读进度线");
  assert.equal(progress.style.transform, "scaleX(0.5)");
  assert.equal(window.document.body.classList.contains("aoi-reading-active"), true);

  dom.window.close();
});

test("does not initialize article reading UI on a date-like non-post page", () => {
  const dom = createPostDom(`
    <main class="page-content"><h1>Not found</h1></main>
  `);
  const { document } = dom.window;

  runReadingScript(dom);

  assert.equal(document.body.hasAttribute("data-aoi-post-reading"), false);
  assert.equal(document.body.classList.contains("aoiblog-post"), false);
  assert.equal(document.querySelector(".aoiblog-paper-texture"), null);
  assert.equal(document.querySelector(".aoi-reading-progress"), null);

  dom.window.close();
});

test("remeasures reading progress when article content height changes", () => {
  const dom = createPostDom(
    `<article class="post-content"><div class="markdown-body"><p>正文</p></div></article>`,
  );
  const { window } = dom;
  const observers = [];
  window.ResizeObserver = class {
    constructor(callback) {
      this.callback = callback;
      observers.push(this);
    }

    observe(target) {
      this.target = target;
    }
  };

  runReadingScript(dom);
  window.scrollY = 400;
  window.dispatchEvent(new window.Event("scroll"));
  assert.equal(
    window.document.querySelector(".aoi-reading-progress__bar").style.transform,
    "scaleX(0.5)",
  );
  assert.equal(observers.length, 1);

  const markdown = window.document.querySelector(".markdown-body");
  markdown.getBoundingClientRect = () => ({
    top: 100 - window.scrollY,
    bottom: 1800 - window.scrollY,
    left: 0,
    right: 720,
    width: 720,
    height: 1700,
    x: 0,
    y: 100 - window.scrollY,
    toJSON() {},
  });
  observers[0].callback([{ target: markdown }]);

  assert.equal(
    window.document.querySelector(".aoi-reading-progress__bar").style.transform,
    "scaleX(0.25)",
  );

  dom.window.close();
});

test("mobile TOC is idempotent and restores focus when Escape closes it", async () => {
  const dom = createPostDom(`
    <button id="before">打开前焦点</button>
    <article class="post-content">
      <div class="markdown-body"><h2 id="section">章节</h2></div>
    </article>
    <aside><div id="toc-body"><a class="tocbot-link" href="#section">章节</a></div></aside>
  `);
  const { window } = dom;
  const triggerBeforeOpen = window.document.getElementById("before");
  triggerBeforeOpen.focus();

  runReadingScript(dom);
  runReadingScript(dom);
  await waitForDomWork(window);

  assert.equal(window.document.querySelectorAll("#aoi-toc-btn").length, 1);
  assert.equal(window.document.querySelectorAll("#aoi-toc-panel").length, 1);

  const button = window.document.getElementById("aoi-toc-btn");
  button.focus();
  button.click();
  assert.equal(window.document.body.classList.contains("aoi-toc-open"), true);
  assert.equal(window.document.activeElement.id, "aoi-toc-close");

  window.document.dispatchEvent(
    new window.KeyboardEvent("keydown", { key: "Escape", bubbles: true }),
  );
  assert.equal(window.document.body.classList.contains("aoi-toc-open"), false);
  assert.equal(window.document.activeElement, button);

  dom.window.close();
});

test("closed mobile TOC is inert and becomes inert again after closing", async () => {
  const dom = createPostDom(`
    <article class="post-content">
      <div class="markdown-body"><h2 id="section">章节</h2></div>
    </article>
    <aside><div id="toc-body"><a class="tocbot-link" href="#section">章节</a></div></aside>
  `);
  const { window } = dom;

  runReadingScript(dom);
  await waitForDomWork(window);

  const panel = window.document.getElementById("aoi-toc-panel");
  const button = window.document.getElementById("aoi-toc-btn");
  assert.equal(panel.hasAttribute("inert"), true);

  button.click();
  assert.equal(panel.hasAttribute("inert"), false);

  window.document.dispatchEvent(
    new window.KeyboardEvent("keydown", { key: "Escape", bubbles: true }),
  );
  assert.equal(panel.hasAttribute("inert"), true);

  dom.window.close();
});

test("open mobile TOC traps keyboard focus inside the dialog", async () => {
  const dom = createPostDom(`
    <article class="post-content">
      <div class="markdown-body"><h2 id="section">章节</h2></div>
    </article>
    <aside><div id="toc-body"><a class="tocbot-link" href="#section">章节</a></div></aside>
  `);
  const { window } = dom;

  runReadingScript(dom);
  await waitForDomWork(window);

  window.document.getElementById("aoi-toc-btn").click();
  const closeButton = window.document.getElementById("aoi-toc-close");
  const lastLink = window.document.querySelector("#aoi-toc-panel .tocbot-link");
  lastLink.focus();
  lastLink.dispatchEvent(
    new window.KeyboardEvent("keydown", {
      key: "Tab",
      bubbles: true,
      cancelable: true,
    }),
  );

  assert.equal(window.document.activeElement, closeButton);

  dom.window.close();
});

test("code wrapping toggles per block without changing copied code", () => {
  const dom = createPostDom(`
    <article class="post-content">
      <div class="markdown-body">
        <pre><code>const longLine = "unchanged";</code></pre>
        <figure class="highlight python"><table><tbody><tr><td><pre><span class="line">print("unchanged")</span></pre></td></tr></tbody></table></figure>
      </div>
    </article>
  `);
  const { window } = dom;

  runReadingScript(dom);

  const toggles = window.document.querySelectorAll(".aoi-code-wrap-toggle");
  const blocks = window.document.querySelectorAll(".aoi-code-block");
  assert.equal(toggles.length, 2);
  assert.equal(blocks.length, 2);

  const originalCode = blocks[0].textContent;
  toggles[0].click();
  assert.equal(blocks[0].classList.contains("is-code-wrapped"), true);
  assert.equal(toggles[0].getAttribute("aria-pressed"), "true");
  assert.equal(blocks[1].classList.contains("is-code-wrapped"), false);
  assert.equal(blocks[0].textContent, originalCode);

  dom.window.close();
});

test("wraps content tables but leaves syntax-highlight tables untouched", () => {
  const dom = createPostDom(`
    <article class="post-content">
      <div class="markdown-body">
        <table id="content-table"><tbody><tr><td>内容</td></tr></tbody></table>
        <figure class="highlight"><table id="code-table"><tbody><tr><td>代码</td></tr></tbody></table></figure>
      </div>
    </article>
  `);
  const { window } = dom;

  runReadingScript(dom);

  const contentTable = window.document.getElementById("content-table");
  const codeTable = window.document.getElementById("code-table");
  assert.equal(contentTable.parentElement.classList.contains("aoi-table-scroll"), true);
  assert.equal(contentTable.parentElement.tabIndex, 0);
  assert.equal(codeTable.parentElement.classList.contains("aoi-table-scroll"), false);

  dom.window.close();
});

test("highlight wrapping changes code whitespace without changing figure table layout", () => {
  const dom = new JSDOM(`
    <!doctype html>
    <html>
      <head><style>${postCssSource}</style></head>
      <body>
        <article class="post-content">
          <figure class="highlight aoi-code-block is-code-wrapped">
            <table><tbody><tr>
              <td class="gutter"><pre>1</pre></td>
              <td class="code"><pre>long code</pre></td>
            </tr></tbody></table>
          </figure>
        </article>
      </body>
    </html>
  `);
  const { window } = dom;
  const figure = window.document.querySelector("figure");
  const table = window.document.querySelector("table");
  const gutterPre = window.document.querySelector(".gutter pre");
  const codeCell = window.document.querySelector(".code");
  const codePre = window.document.querySelector(".code pre");

  assert.notEqual(window.getComputedStyle(figure).whiteSpace, "pre-wrap");
  assert.notEqual(window.getComputedStyle(table).tableLayout, "fixed");
  assert.notEqual(window.getComputedStyle(gutterPre).whiteSpace, "pre-wrap");
  assert.equal(window.getComputedStyle(codeCell).verticalAlign, "top");
  assert.equal(window.getComputedStyle(codePre).whiteSpace, "pre-wrap");

  dom.window.close();
});

test("indents only top-level text paragraphs in article content", () => {
  const dom = new JSDOM(`
    <!doctype html>
    <html>
      <head><style>${postCssSource}</style></head>
      <body>
        <article class="post-content">
          <div class="markdown-body">
            <p id="text-paragraph">正文段落</p>
            <p id="image-paragraph"><img src="/images/example.png" alt="示例"></p>
            <blockquote><p id="quote-paragraph">引用段落</p></blockquote>
          </div>
        </article>
      </body>
    </html>
  `);
  const { window } = dom;

  assert.equal(
    window.getComputedStyle(window.document.getElementById("text-paragraph")).textIndent,
    "2em",
  );
  assert.notEqual(
    window.getComputedStyle(window.document.getElementById("image-paragraph")).textIndent,
    "2em",
  );
  assert.notEqual(
    window.getComputedStyle(window.document.getElementById("quote-paragraph")).textIndent,
    "2em",
  );

  dom.window.close();
});

test("homepage article titles override Fluid truncation and remain fully visible", () => {
  const dom = new JSDOM(`
    <!doctype html>
    <html>
      <head>
        <style>
          .index-header {
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            display: -webkit-box;
            -webkit-line-clamp: 2;
          }
        </style>
        <style>${homeCssSource}</style>
      </head>
      <body>
        <main id="board">
          <h2 class="index-header">
            <a>2026年的这个夏天，我究竟在如何理解这个世界？</a>
          </h2>
        </main>
      </body>
    </html>
  `);
  const title = dom.window.document.querySelector(".index-header");
  const style = dom.window.getComputedStyle(title);

  assert.equal(style.whiteSpace, "normal");
  assert.equal(style.overflow, "visible");
  assert.equal(style.textOverflow, "clip");
  assert.equal(style.getPropertyValue("-webkit-line-clamp"), "none");

  dom.window.close();
});

test("the deleted essay URL permanently redirects to the current essay URL", () => {
  const redirect = vercelConfig.redirects?.find((entry) => (
    entry.source === "/2026/07/31/2026-nian-de-zhe-ge-xia-tian-wo-jiu-jing-zai-ru-he-li-jie-zhe-ge-shi-jie/"
  ));
  assert.deepEqual(redirect, {
    source: "/2026/07/31/2026-nian-de-zhe-ge-xia-tian-wo-jiu-jing-zai-ru-he-li-jie-zhe-ge-shi-jie/",
    destination: "/2026/07/31/2026-nian-xia-tian-de-wo-jiu-jing-zai-ru-he-li-jie-zhe-ge-shi-jie/",
    permanent: true,
  });
});
