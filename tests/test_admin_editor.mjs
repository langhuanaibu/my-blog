import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { readFile } from "node:fs/promises";
import test from "node:test";
import vm from "node:vm";

const require = createRequire(import.meta.url);
let editorTools = null;
try {
  editorTools = require("../source/admin/editor-tools.js");
} catch {
  // The first TDD run deliberately proves the helper does not exist yet.
}

test("Word clipboard text becomes blank-line-separated Markdown paragraphs", () => {
  assert.ok(editorTools, "editor tools module should exist");
  const result = editorTools.wordPasteReplacement({
    html: '<html xmlns:o="urn:schemas-microsoft-com:office:office"><p class="MsoNormal">第一段</p><p class="MsoNormal">第二段</p></html>',
    text: "第一段\r\n第二段\r\n\r\n第三段",
    value: "开头\n\n结尾",
    selectionStart: 4,
    selectionEnd: 4,
  });

  assert.deepEqual(result, {
    value: "开头\n\n第一段\n\n第二段\n\n第三段结尾",
    selectionStart: 17,
    selectionEnd: 17,
  });
});

test("non-Word clipboard content is left to the browser", () => {
  assert.ok(editorTools, "editor tools module should exist");
  assert.equal(editorTools.wordPasteReplacement({
    html: "<p>普通网页</p>",
    text: "普通网页",
    value: "",
    selectionStart: 0,
    selectionEnd: 0,
  }), null);
});

test("Enter creates a paragraph and replaces the current selection", () => {
  assert.ok(editorTools, "editor tools module should exist");
  assert.deepEqual(editorTools.editorEnterReplacement({
    value: "第一段待替换文字",
    selectionStart: 3,
    selectionEnd: 7,
    shiftKey: false,
  }), {
    value: "第一段\n\n字",
    selectionStart: 5,
    selectionEnd: 5,
  });
});

test("Shift+Enter writes a portable Markdown hard break", () => {
  assert.ok(editorTools, "editor tools module should exist");
  assert.deepEqual(editorTools.editorEnterReplacement({
    value: "同一段",
    selectionStart: 3,
    selectionEnd: 3,
    shiftKey: true,
  }), {
    value: "同一段  \n",
    selectionStart: 6,
    selectionEnd: 6,
  });
});

test("Shift+Enter replaces the selected text with a portable hard break", () => {
  assert.ok(editorTools, "editor tools module should exist");
  assert.deepEqual(editorTools.editorEnterReplacement({
    value: "before selected after",
    selectionStart: 6,
    selectionEnd: 16,
    shiftKey: true,
  }), {
    value: "before  \nafter",
    selectionStart: 9,
    selectionEnd: 9,
  });
});

test("Markdown structures keep standard single-line Enter behavior", () => {
  assert.ok(editorTools, "editor tools module should exist");
  const cases = [
    "- 列表项",
    "> 引用",
    "| 表格 |",
    "Column A | Column B",
    "# 标题",
    "```js\nconst value = 1;",
  ];

  for (const value of cases) {
    const result = editorTools.editorEnterReplacement({
      value,
      selectionStart: value.length,
      selectionEnd: value.length,
      shiftKey: false,
    });
    assert.equal(result.value, `${value}\n`, value);
  }
});

test("Markdown import normalizes BOM and CRLF before reading front matter and a leading H1", () => {
  assert.ok(editorTools, "editor tools module should exist");
  assert.deepEqual(editorTools.markdownImportReplacement({
    source: '\uFEFF---\r\ntitle: "Front matter title"\r\n---\r\n\r\n# Imported title\r\nFirst paragraph\r\nSecond paragraph\r\n',
    title: "",
    value: "unchanged",
  }), {
    title: "Imported title",
    value: "First paragraph\n\nSecond paragraph",
  });
});

test("Markdown import changes only top-level prose soft breaks", () => {
  assert.ok(editorTools, "editor tools module should exist");
  const source = [
    "First prose line",
    "Second prose line",
    "Hard break with spaces  ",
    "same paragraph after spaces",
    "Hard break with slash\\",
    "same paragraph after slash",
    "Literal slash pair\\\\",
    "new paragraph after literal slashes",
    "",
    "Setext heading",
    "--------------",
    "",
    "- list item",
    "  continuation",
    "  - nested item",
    "",
    "> quote line",
    "> quote continuation",
    "",
    "Column A | Column B",
    "-------- | --------",
    "one | two",
    "",
    "| Left | Right |",
    "| --- | --- |",
    "| a | b |",
    "",
    "```js",
    "const value = 1;",
    "```",
    "",
    "    indented code",
    "",
    "<section>",
    "raw html",
    "</section>",
    "",
    "[ref]: https://example.com",
    "[^note]: footnote definition",
    "",
    "![image](/images/example.webp)",
  ].join("\n");

  const result = editorTools.markdownImportReplacement({
    source,
    title: "Existing title",
    value: "unchanged",
  });

  assert.equal(result.title, "Existing title");
  assert.match(result.value, /^First prose line\n\nSecond prose line/);
  assert.match(result.value, /Hard break with spaces  \nsame paragraph after spaces/);
  assert.match(result.value, /Hard break with slash\\\nsame paragraph after slash/);
  assert.match(result.value, /Literal slash pair\\\\\n\nnew paragraph after literal slashes/);
  for (const structure of [
    "Setext heading\n--------------",
    "- list item\n  continuation\n  - nested item",
    "> quote line\n> quote continuation",
    "Column A | Column B\n-------- | --------\none | two",
    "| Left | Right |\n| --- | --- |\n| a | b |",
    "```js\nconst value = 1;\n```",
    "    indented code",
    "<section>\nraw html\n</section>",
    "[ref]: https://example.com",
    "[^note]: footnote definition",
    "![image](/images/example.webp)",
  ]) {
    assert.ok(result.value.includes(structure), structure);
  }
});

test("Markdown import preserves existing blank lines", () => {
  assert.ok(editorTools, "editor tools module should exist");
  const result = editorTools.markdownImportReplacement({
    source: "First paragraph\n\nSecond paragraph\n\n\nThird paragraph",
    title: "",
    value: "unchanged",
  });
  assert.equal(result.value, "First paragraph\n\nSecond paragraph\n\n\nThird paragraph");
});

test("Markdown import never mistakes a multiline reference definition for prose", () => {
  assert.ok(editorTools, "editor tools module should exist");
  const source = [
    '[reference]: /target "Repeated',
    'prose"',
    "",
    "Repeated",
    "prose",
  ].join("\n");
  const result = editorTools.markdownImportReplacement({ source, title: "", value: "unchanged" });
  assert.equal(result.value, [
    '[reference]: /target "Repeated',
    'prose"',
    "",
    "Repeated",
    "",
    "prose",
  ].join("\n"));
});

test("Markdown import preserves definition-like text inside fenced code", () => {
  assert.ok(editorTools, "editor tools module should exist");
  const source = [
    "```markdown",
    "[reference]: /target",
    "```",
  ].join("\n");
  assert.equal(
    editorTools.markdownImportReplacement({ source, title: "", value: "unchanged" }).value,
    source,
  );
});

test("Markdown import keeps definition-like lines that belong to a prose paragraph", () => {
  assert.ok(editorTools, "editor tools module should exist");
  const source = [
    "Intro",
    "[reference]: /target",
    "Continuation",
  ].join("\n");
  assert.equal(
    editorTools.markdownImportReplacement({ source, title: "", value: "unchanged" }).value,
    ["Intro", "", "[reference]: /target", "", "Continuation"].join("\n"),
  );
});

test("Markdown import failure leaves the current editor state available to the caller", () => {
  assert.ok(editorTools, "editor tools module should exist");
  assert.throws(
    () => editorTools.markdownImportReplacement({
      source: "Replacement",
      title: "Current title",
      value: "Current body",
      lexer: () => { throw new Error("parser failed"); },
    }),
    /parser failed/,
  );
});

test("admin loads the vendored Markdown parser before editor tools", async () => {
  const html = await readFile(new URL("../source/admin/index.html", import.meta.url), "utf8");
  const markedIndex = html.indexOf('<script src="/admin/marked.min.js"></script>');
  const toolsIndex = html.indexOf('<script src="/admin/editor-tools.js"></script>');
  assert.ok(markedIndex >= 0);
  assert.ok(toolsIndex > markedIndex);
  const markedSource = await readFile(new URL("../source/admin/marked.min.js", import.meta.url), "utf8");
  assert.match(markedSource, /marked/i);
});

test("vendored Marked and editor tools work together through browser globals", async () => {
  const context = vm.createContext({});
  const markedSource = await readFile(new URL("../source/admin/marked.min.js", import.meta.url), "utf8");
  const toolsSource = await readFile(new URL("../source/admin/editor-tools.js", import.meta.url), "utf8");
  vm.runInContext(markedSource, context);
  vm.runInContext(toolsSource, context);
  const result = context.AoiAdminEditorTools.markdownImportReplacement({
    source: "First line\nSecond line",
    title: "",
    value: "unchanged",
  });
  assert.equal(result.value, "First line\n\nSecond line");
});

test("browser editor reports a missing Markdown parser instead of changing content", async () => {
  const context = vm.createContext({});
  const toolsSource = await readFile(new URL("../source/admin/editor-tools.js", import.meta.url), "utf8");
  vm.runInContext(toolsSource, context);
  assert.throws(
    () => context.AoiAdminEditorTools.markdownImportReplacement({
      source: "Replacement",
      title: "Current title",
      value: "Current body",
    }),
    /parser is unavailable/,
  );
});
