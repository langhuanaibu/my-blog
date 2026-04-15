# Pretext 优化个人博客实施计划

## 摘要
利用 `@chenglou/pretext`（一个极速、不依赖 DOM 的多行文本测量与布局引擎）对博客进行前端性能与视觉上的优化。主要实现三个方向：首页文章摘要的精准多行截断、文章列表的高性能虚拟化渲染，以及首页卡片的瀑布流布局。这些优化将避免 DOM 测量带来的重排（Reflow），显著提升页面性能和阅读体验。

## 当前状态分析
1. **首页文章摘要**：`index.astro` 中目前使用 `substring(0, 100)` 简单粗暴地截取前 100 个字符。这种做法无法感知字符的真实渲染宽度，常导致半个单词被截断，且卡片高度不一。
2. **文章列表渲染**：`articles.html.astro` 中的左侧文章列表是一次性将所有文章渲染进 `#articles-nav`。随着文章数量增加，DOM 节点数成正比增长，容易导致页面卡顿。
3. **卡片布局**：分类卡片和文章卡片使用 CSS Grid 布局，若内容长度差异大，卡片底部会留白较多，不够紧凑。

## 拟定修改与实现细节

### 1. 引入 Pretext 依赖
由于项目是 Astro 且客户端脚本较多，我们将通过 jsDelivr CDN 以 ES Module 形式引入 Pretext：
- CDN 地址：`https://cdn.jsdelivr.net/npm/@chenglou/pretext@0.0.5/dist/layout.js`

### 2. 首页摘要精准多行截断 (index.astro)
- **文件**：`src/pages/index.astro`
- **实现方案**：
  - 修改 `initLatestArticles` 中的 `<script is:inline>` 为 `<script type="module">`，以便导入 Pretext。
  - 在生成摘要时，预估或获取 `.blog-card` 的文本内容宽度（例如默认 300px）。
  - 使用 `prepareWithSegments`（字体如 `'14px system-ui'`）和 `layoutWithLines` 计算摘要文本。
  - 精确提取前 3 行文本并拼接，若总行数超过 3 行则追加 `...`。
  - **优势**：完美适配容器宽度，保证截断视觉上的完美对齐，取代不可控的 CSS `-webkit-line-clamp`。

### 3. 长文章列表虚拟化渲染 (articles.html.astro)
- **文件**：`src/pages/articles.html.astro`
- **实现方案**：
  - 修改 `<script is:inline>` 为 `<script type="module">`。
  - 在 `renderArticlesList` 中，使用 `prepare` 和 `layout` 预先计算出每篇文章标题在列表宽度（约 240px）下的精确高度。结合固定的内外边距，得出每个列表项的绝对高度。
  - 计算出每个列表项的 `top` 偏移量和整个列表的 `totalHeight`。
  - 在 `#articles-nav` 内部创建一个撑开滚动条的虚拟占位容器（高度为 `totalHeight`）。
  - 监听 `#articles-nav` 的 `scroll` 事件，根据 `scrollTop` 和 `clientHeight` 仅渲染可视区域内的文章节点（加上下缓冲区域），并使用 `transform: translateY(top)` 绝对定位这些节点。
  - **优势**：无论文章达到几千篇，DOM 节点数始终保持在几十个以内，实现 60fps 极速滚动。

### 4. 首页分类卡片高性能瀑布流 (index.astro)
- **文件**：`src/pages/index.astro`
- **实现方案**：
  - 针对 `#dynamic-categories-grid`，使用 Pretext 预先计算分类描述文本的精确高度。
  - 结合图标和标题的固定高度，得出每个卡片的总高度。
  - 维护一个包含两列（或多列，视屏幕宽度而定）高度的数组。遍历每个卡片，将其放置在当前高度最小的列中，更新该列高度。
  - 最终将计算出的 `top` 和 `left` 直接应用到生成的 HTML 字符串中，无需插入 DOM 后再测量。
  - **优势**：避免了传统瀑布流插件必须先渲染到 DOM 然后再读取 `offsetHeight` 引起的严重布局抖动（Layout Thrashing）。

## 假设与决策
- **模块化改造**：Astro 中的 `is:inline` 脚本若要使用 `import`，需更改为 `<script type="module">`。这会将脚本执行时机推迟到 DOM 解析之后（即 `defer`），但这与现有的 `DOMContentLoaded` 逻辑完美契合。
- **字体匹配**：Pretext 需要知道准确的字体以进行画布测量，我们将默认使用 `'system-ui'` 并在必要时匹配 CSS 变量 `--font-body` 的设定。

## 验证步骤
1. 打开首页，检查最新文章的摘要是否精准截断为 3 行。
2. 打开文章页，向列表中注入大量模拟文章（或滚动现有文章），检查 DOM 元素是否随滚动动态复用，且没有滚动条抖动。
3. 检查首页分类卡片是否呈现交错紧凑的瀑布流排版。