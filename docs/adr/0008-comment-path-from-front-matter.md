# 评论 path 由 front-matter 决定，而不是迁移评论数据

迁移到 Hexo Fluid 之后，每篇文章其实渲染了**两个**评论区：正文尾部有迁移工具注入的 `<section class="legacy-comments">`，被 `source/js/twikoo-legacy-path.js` 挂载；文末又有 Fluid 自己的评论区。两个元素抢用同一个 `id="twikoo"`，页面上同时跑着两个 Twikoo 版本（CDN 1.6.32 与主题内置 1.6.8）。

更糟的是 Fluid 那一个从来就没工作过。`_config.fluid.yml` 里配了 `twikoo.path: window.location.pathname`，但主题模板写的是 `path: '<%= theme.twikoo.path %>'`——带引号且转义，线上输出的是字面量字符串 `'window.location.pathname'`。所有文章的文末评论区因此共用同一个 path 桶，任何人在这里发的评论都会出现在全部文章下面。查该桶实测 0 条，说明迁移至今没有人从这里成功评论过；42 条真实评论全部挂在旧 `article_id` 上，只有正文里那个 legacy 块能读到。

要归一成单个评论区，就必须回答：那 42 条评论怎么办。

选择的做法是**不动 Twikoo 数据库，改渲染**。`scripts/twikoo-path.js` 注册 `theme_inject` 过滤器，以同名 `default` 覆盖 Fluid 的 `postComments` / `pageComments` 注入点，path 取 `page.twikooPath || url_for(page.path)`。19 篇旧文的 front-matter 里本来就存着 `twikooPath`（迁移时留下的旧 `article_id`），于是历史评论零迁移地出现在正确位置；新文章没有该字段，自动回落到真实 URL 路径。正文里的 legacy 块随之删除。

这条路可行是因为两个已验证的机制：Fluid 的注入点走 `this.partial(layout, locals)`，而 Hexo 的 partial 做 `Object.assign(viewLocals, this, locals)`，所以注入的片段能读到 `page`；注入项按 `inject/<point>/<name>` 去重，同名后注册覆盖先注册，因此不必改主题源码。Hexo 原生的 `injector` 不行——它对函数值是注册时求值一次并按页面类型缓存，拿不到单篇上下文。

## Considered Options

- **迁移评论数据**：通过 Twikoo 后台导出 JSON、把 `url` 字段从 `article_id` 改成新的 URL 路径、再导入。数据库层面最干净，`twikooPath` 从此退役。否决原因是这是一次不可回滚的手工操作，导入出错就丢评论；而收益仅仅是省掉一个 front-matter 字段。
- **只修 path bug，保留双评论区**：删掉 `_config.fluid.yml` 那行坏配置让 Twikoo 回落到真实 pathname 即可，改动一行。但双评论区、`id` 冲突和两个 Twikoo 版本竞争都还在，而且新旧评论从此分裂在两个区里。
- **反过来关掉 Fluid 评论区，只留正文内的 legacy 块**：旧评论零风险。但新文章得手写 HTML 挂载块，且评论区位置在版权和上下篇之上，排版是错的。

## Consequences

- **`twikooPath` 与 `old_id` 从"迁移遗留字段"升级为运行时依赖**。改动或删除它们会直接断开历史评论，这一点已写进 readme 的迁移记录。
- 留言板走同一套机制，front-matter 写 `comment: true` 与 `twikooPath: "/"`。**必须是单数 `comment`**：Fluid 的 `post-filter.js` 在 `before_generate` 阶段用单数 `comment` 重写每个页面的 `page.comments`，写复数会被覆盖成 `false`，评论区直接不渲染。
- `source/js/twikoo-legacy-path.js` 保留但事实上退役。它以 `[data-twikoo-path]` 是否存在为开关，正文清空后在文章页和留言板都不再动作。留着是因为它同时负责清理旧的 `aoiblog_admin_token`。
- 覆盖主题注入点意味着**升级 Fluid 时要复核**：如果上游改了 `layout/_partials/comments/twikoo.ejs` 的结构或 `Fluid.utils.loadComments` 的用法，本仓库这份副本不会自动跟进。
- 未来若真要迁移评论数据，这个方案不构成阻碍——把数据迁好后删掉 front-matter 字段即可，path 会自动回落到 URL 路径。
