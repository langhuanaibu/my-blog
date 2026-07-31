(function initAdminEditorTools(root, factory) {
  const tools = factory();
  if (typeof module === "object" && module.exports) module.exports = tools;
  if (root) root.AoiAdminEditorTools = tools;
}(typeof globalThis !== "undefined" ? globalThis : this, function createAdminEditorTools() {
  function replaceSelection(value, selectionStart, selectionEnd, insertedText) {
    const nextValue = value.slice(0, selectionStart) + insertedText + value.slice(selectionEnd);
    const nextSelection = selectionStart + insertedText.length;
    return {
      value: nextValue,
      selectionStart: nextSelection,
      selectionEnd: nextSelection,
    };
  }

  function isWordHtml(html) {
    return /(?:\bMso[A-Za-z]|\bmso-|urn:schemas-microsoft-com:office|Microsoft Word)/i.test(String(html || ""));
  }

  function normalizeWordText(text) {
    const lines = String(text || "")
      .replace(/\r\n?/g, "\n")
      .split("\n")
      .map((line) => line.replace(/[\t ]+$/g, ""));

    while (lines.length && !lines[0].trim()) lines.shift();
    while (lines.length && !lines[lines.length - 1].trim()) lines.pop();

    return lines.filter((line) => line.trim()).join("\n\n");
  }

  function wordPasteReplacement({ html, text, value, selectionStart, selectionEnd }) {
    if (!isWordHtml(html)) return null;
    return replaceSelection(
      String(value || ""),
      selectionStart,
      selectionEnd,
      normalizeWordText(text),
    );
  }

  function isInsideFence(value, position) {
    const lines = value.slice(0, position).split("\n");
    let fence = "";
    for (const line of lines) {
      const match = /^\s*(`{3,}|~{3,})/.exec(line);
      if (!match) continue;
      const marker = match[1][0];
      if (!fence) fence = marker;
      else if (fence === marker) fence = "";
    }
    return Boolean(fence);
  }

  function currentLine(value, position) {
    const beforeCursor = value.slice(0, position);
    const start = beforeCursor.lastIndexOf("\n") + 1;
    return beforeCursor.slice(start);
  }

  function isMarkdownStructure(value, position) {
    if (isInsideFence(value, position)) return true;
    const line = currentLine(value, position);
    return /^\s*(?:[-+*]\s+|\d+[.)]\s+|>\s?|#{1,6}\s+|`{3,}|~{3,}| {4}\S)/.test(line)
      || /^\s*\|.*\|\s*$/.test(line)
      || /\S\s*\|\s*\S/.test(line);
  }

  function editorEnterReplacement({ value, selectionStart, selectionEnd, shiftKey }) {
    const text = String(value || "");
    const line = currentLine(text, selectionStart);
    const useSingleBreak = shiftKey
      || !line.trim()
      || isMarkdownStructure(text, selectionStart);
    return replaceSelection(
      text,
      selectionStart,
      selectionEnd,
      useSingleBreak ? "\n" : "\n\n",
    );
  }

  return {
    editorEnterReplacement,
    normalizeWordText,
    wordPasteReplacement,
  };
}));
