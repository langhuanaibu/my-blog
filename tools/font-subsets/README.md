# News serif font subset

`news-serif-sc.txt` is the deterministic character allowlist used by the news page's self-hosted Noto Serif SC 700 webfont. It contains printable ASCII, common full-width punctuation, and the 600 most frequent Han characters in the committed news UI and report corpus. Characters outside this list intentionally fall back to the system serif stack. The compact allowlist keeps the complete cold font transfer below 500 KB.

Regenerate the committed list from a fixed repository state:

```powershell
node tools/font-subsets/build-news-serif-chars.cjs
```

The webfont itself is generated with `cn-font-split@7.4.3` through `tools/generate-news-font.cjs`. Keep only the resulting WOFF2 and `result.css` beside `OFL.txt`; the source OTF, `index.proto`, previews, and temporary dependencies are build inputs and must not be committed. The source font version, SHA-256, full command, Windows caveat, and fallback contract are documented in the root `readme.md`.
