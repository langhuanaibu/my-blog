(function initAdminEditorTools(root, factory) {
  const tools = factory(root);
  if (typeof module === "object" && module.exports) module.exports = tools;
  if (root) root.AoiAdminEditorTools = tools;
}(typeof globalThis !== "undefined" ? globalThis : this, function createAdminEditorTools(root) {
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
    const useSingleBreak = !line.trim()
      || isMarkdownStructure(text, selectionStart);
    return replaceSelection(
      text,
      selectionStart,
      selectionEnd,
      shiftKey ? "  \n" : useSingleBreak ? "\n" : "\n\n",
    );
  }

  function markedApi() {
    if (root?.marked?.lexer) return root.marked;
    if (typeof require === "function") {
      const markedModule = require("marked");
      const marked = markedModule.marked || markedModule;
      if (marked?.lexer) return markedModule.Lexer ? markedModule : marked;
    }
    throw new Error("Markdown parser is unavailable");
  }

  function defaultLexer(source) {
    return markedApi().lexer(source, { gfm: true });
  }

  function tokenContainsRange(source, tokens, range) {
    for (const token of tokens) {
      if (!token.raw) continue;
      let position = source.indexOf(token.raw);
      while (position >= 0) {
        if (position <= range.start && position + token.raw.length >= range.contentEnd) {
          return true;
        }
        position = source.indexOf(token.raw, position + 1);
      }
    }
    return false;
  }

  function referenceDefinitionRanges(source, tokens) {
    const rule = markedApi().Lexer?.rules?.block?.gfm?.def;
    if (!rule) return [];
    const ranges = [];
    let position = 0;
    while (position < source.length) {
      rule.lastIndex = 0;
      const match = rule.exec(source.slice(position));
      if (match) {
        const trailingNewlines = /\n+$/.exec(match[0])?.[0].length || 0;
        const range = {
          start: position,
          end: position + match[0].length,
          contentEnd: position + match[0].length - trailingNewlines,
        };
        if (!tokenContainsRange(source, tokens, range)) ranges.push(range);
        position += match[0].length;
        continue;
      }
      const newline = source.indexOf("\n", position);
      if (newline < 0) break;
      position = newline + 1;
    }
    return ranges;
  }

  function tokenStartOutsideRanges(source, raw, cursor, ranges) {
    let position = source.indexOf(raw, cursor);
    while (position >= 0) {
      const end = position + raw.length;
      const overlapsDefinition = ranges.some((range) => position < range.end && end > range.start);
      if (!overlapsDefinition) return position;
      position = source.indexOf(raw, position + 1);
    }
    return -1;
  }

  function splitImportedMarkdown(source) {
    let body = String(source || "")
      .replace(/^\uFEFF/, "")
      .replace(/\r\n?/g, "\n");
    body = body.replace(/^---\n[\s\S]*?\n---(?:\n|$)/, "");

    const leadingHeading = /^(?:[ \t]*\n)*#\s+([^\n]+)(?:\n|$)/.exec(body);
    const title = leadingHeading ? leadingHeading[1].trim() : "";
    if (leadingHeading) body = body.slice(leadingHeading[0].length);

    return { title, body: body.replace(/^\n+|\n+$/g, "") };
  }

  function normalizeParagraphToken(raw) {
    if (/^\[\^[^\]]+\]:/.test(raw)) return raw;
    const lines = raw.split("\n");
    let result = lines[0] || "";
    for (let index = 1; index < lines.length; index += 1) {
      const previous = lines[index - 1];
      const trailingSlashes = /\\+$/.exec(previous)?.[0].length || 0;
      const hardBreak = / {2,}$/.test(previous) || trailingSlashes % 2 === 1;
      result += `${hardBreak ? "\n" : "\n\n"}${lines[index]}`;
    }
    return result;
  }

  function markdownImportReplacement({ source, title, lexer }) {
    const imported = splitImportedMarkdown(source);
    const tokens = (lexer || defaultLexer)(imported.body);
    if (!Array.isArray(tokens)) throw new Error("Markdown parser returned invalid tokens");
    const definitionRanges = referenceDefinitionRanges(imported.body, tokens);
    let cursor = 0;
    let value = "";
    for (const token of tokens) {
      if (!token.raw) continue;
      const tokenStart = tokenStartOutsideRanges(
        imported.body,
        token.raw,
        cursor,
        token.type === "paragraph" ? definitionRanges : [],
      );
      if (tokenStart < 0) throw new Error("Markdown parser returned inconsistent tokens");
      value += imported.body.slice(cursor, tokenStart);
      value += token.type === "paragraph" ? normalizeParagraphToken(token.raw) : token.raw;
      cursor = tokenStart + token.raw.length;
    }
    value = `${value}${imported.body.slice(cursor)}`.replace(/^\n+|\n+$/g, "");
    return {
      title: String(title || "") || imported.title,
      value,
    };
  }

  return {
    editorEnterReplacement,
    markdownImportReplacement,
    normalizeWordText,
    wordPasteReplacement,
  };
}));
