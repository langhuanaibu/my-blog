# News serif font subset

`news-serif-sc.txt` is the **first-paint hot set** for the news page's self-hosted Noto Serif SC 700 webfont — printable ASCII, common full-width punctuation, and every Han character that appears in the committed news UI and report corpus.

It is **not** a coverage contract. `tools/generate-news-font.cjs` runs with `subsetRemainChars`, so every glyph outside this list stays available in auto-chunked tail files and is fetched on demand through `unicode-range`. Nothing falls back to the system serif. The list only decides how many chunks a typical page has to download, so a growing corpus never causes missing glyphs and the list does **not** need periodic regeneration.

Regenerate it (optional, to re-tune first-paint bytes) from a fixed repository state:

```powershell
node tools/font-subsets/build-news-serif-chars.cjs
```

Output is sorted by code point, so the same repository state always produces the same bytes.

The webfont itself is generated with `cn-font-split@7.4.3` through `tools/generate-news-font.cjs`. Keep only the resulting WOFF2 chunks and `result.css` beside `OFL.txt`; the source OTF, `index.proto`, previews, and temporary dependencies are build inputs and must not be committed. The source font version, SHA-256, full command, Windows caveat, and measured cold-load budget are documented in the root `readme.md`.
