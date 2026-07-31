import assert from "node:assert/strict";
import { createRequire } from "node:module";
import test from "node:test";

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

test("Shift+Enter keeps a single Markdown line break", () => {
  assert.ok(editorTools, "editor tools module should exist");
  assert.deepEqual(editorTools.editorEnterReplacement({
    value: "同一段",
    selectionStart: 3,
    selectionEnd: 3,
    shiftKey: true,
  }), {
    value: "同一段\n",
    selectionStart: 4,
    selectionEnd: 4,
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
