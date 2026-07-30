# Aoitsuki Blog

这是 Aoitsuki 的个人博客项目，当前采用 `Hexo + Fluid + Vercel` 的静态博客架构。

## 当前架构

- 博客框架：Hexo
- 主题：Fluid
- 内容源：`source/_posts/*.md`
- 静态资源：`source/images/`
- 自定义脚本：`source/js/`（前端）、`scripts/`（Hexo 构建期扩展）
- Vercel API：`api/`（在线后台，以及日报反馈、收藏、稍后读与漏读写回；停用的单词本接口仍保留）
- 在线后台：`/admin/`
- 构建输出：`dist/`
- 部署平台：Vercel
- 评论系统：Twikoo
- 站点域名：`https://aoiblog.top`

## 目录说明

```text
source/_posts/          文章 Markdown
source/images/          图片资源
source/images/covers/   文章封面图
source/js/              自定义前端脚本
source/css/             自定义前端样式
source/admin/           在线后台页面
source/_data/           分类封面等站点数据
api/                    Vercel Serverless API（后台与日报个人状态写回）
source/about/           关于页面
source/friends/         友情链接页面
source/guestbook/       留言板页面
source/news/            每日新闻日报页（静态，数据由 news-pipeline 生成）
news-pipeline/          新闻日报生成管线（GitHub Actions 每日运行）
scripts/                Hexo 构建期扩展（主题注入点覆盖等）
tools/                  迁移和维护工具
docs/                   维护规范与必要的历史记录
docs/archive/           历史架构与迁移记录（非当前运行说明）
_config.yml             Hexo 主配置
_config.fluid.yml       Fluid 主题配置
.vercelignore           Vercel 源文件排除清单
vercel.json             Vercel 路由与安全响应头
```

## 常用命令

安装依赖：

```powershell
npm install
```

本地开发：

```powershell
npm run dev
```

构建：

```powershell
npm run build
```

本地预览：

```powershell
npm run preview
```

新闻页前端回归测试：

```powershell
npm run test:news
```

文章阅读页交互回归测试：

```powershell
npm run test:post
```

## 内容维护

- 在线后台地址是 `/admin/`。登录后可以发布、编辑、删除文章，也可以上传文章封面和正文图片。
- 后台“站点设置”可以修改常用展示文本，包括站点标题、副标题、首页标语、页脚文本、关于页昵称/简介和现有导航显示名；页脚按纯文本保存并进行 HTML 转义。
- 新文章最终会写入 `source/_posts/`。
- 图片统一放入 `source/images/`，文章中使用 `/images/<filename>`；后台上传会校验 PNG、JPEG、GIF、WebP 的文件签名，扩展名与内容不一致时拒绝写入。
- 默认分类封面配置在 `source/_data/category-covers.json`。
- 文章 front matter 中的 `index_img` 是首页卡片封面；如果后台没有上传单篇封面，会自动使用分类默认封面。
- 文章 URL 使用 `/:year/:month/:day/:title/`。
- 迁移自旧站的文章保留 `old_id` 和 `twikooPath` front matter，用于旧链接兼容和 Twikoo 评论路径。

## 在线后台环境变量

部署到 Vercel 后，后台写文章和保存站点设置需要在 Vercel 项目环境变量中配置：

```text
ADMIN_TOKEN=后台登录口令
GITHUB_TOKEN=具有目标仓库 contents 写权限的 GitHub token
GITHUB_OWNER=langhuanaibu
GITHUB_REPO=my-blog
GITHUB_BRANCH=main
```

`ADMIN_TOKEN` 只在登录提交的那一次请求里出现，**换取会话后即从页面内存清除**，既不写 `localStorage`，也不再随后续请求发送。会话是 8 小时有效、`HttpOnly + Secure + SameSite=Strict` 的签名 Cookie，`scope` 参与签名：`admin` 可发文章、改设置、传图，`personal` 只能读写日报反馈、收藏、稍后读和漏读。目前只有 `/admin/` 登录会签发会话，签发的都是 `admin`。GitHub token 始终只保存在服务端环境变量中。这套 scope 设计**刻意放宽了原先「签名 cookie 不得换来发文章权限」的不变式**，换取主口令不再常驻页面内存；取舍理由、被否掉的方案和「看到相关测试别改回去」的提醒见 `docs/adr/0010-admin-writes-accept-scoped-session.md`。

### API 鉴权与并发保护

- 失败锁定由 `api/_loginGuard.js` 统一持有，**Cookie 登录和 `Authorization: Bearer` 共用同一份计数**。这一点是必须的：两条路验的是同一个 `ADMIN_TOKEN`，只给其中一条接限流等于没限流——攻击者换打 `/api/adminArticles` 就能无限次猜口令（2026-07-29 修复）。缺失凭证不计入锁定，只有「带了 `Authorization` 但值不对」才记账，否则未认证探测就能把管理员自己锁在门外。
- `POST /api/adminSession` 校验后台口令并建立个人会话；同一客户端在 15 分钟内连续失败 5 次后，该 Serverless 实例会返回 `429` 与 `Retry-After`，成功登录会清除失败记录。客户端地址优先取 Vercel 提供的 `x-vercel-forwarded-for` 首地址，缺失时回落到通用转发头或 socket 地址。失败记录最多保留 1000 个客户端且只存在当前实例内存中，因此这只是应用层兜底，不替代 Vercel Firewall 等跨实例限流。`GET` 用于探测会话（后台页刷新后据此直接恢复，不再要求重新输入口令），`DELETE` 用于退出。会话 Cookie 仅作用于 `/api`，接口不开放跨域凭据读取；畸形 Cookie 按未登录处理，不产生 500。
- `api/newsState.js` 只接受个人会话，用于日报反馈、收藏、稍后读和漏读；读取使用 `GET /api/newsState?type=feedback|read_later|favorites|misses`，写入使用 `POST /api/newsState` 与 `{ "type": "...", "payload": { ... } }`。单次 payload 上限 4096 字节，各状态最多保留 1000 条；并发写入撞到 GitHub blob SHA 时重读后重试一次。所有状态的 `date` 都必须是真实的 `YYYY-MM-DD` 日历日期，稍后读链接必须是带主机名的有效 HTTP(S) URL。漏读新增 payload 为 `date/title?/url?/reason`，撤销为 `op: "remove"` 加记录 `id`；标题或有效 HTTP(S) URL 至少一个，`reason` 只允许 `important_event`（重要事件）、`deep_read`（值得深读）、`missing_perspective`（缺少视角）。`adminArticles.js`、`adminSettings.js`、`adminUpload.js`、`vocab.js` 这些高权限接口走 `requireAdminWrite`：带 `Authorization` 头时用受限流的 `Bearer <ADMIN_TOKEN>`（留给脚本/CLI），否则认 `scope=admin` 的会话 Cookie（浏览器后台用）。
- 所有 JSON 接口在业务处理前先做请求体体积检查：默认上限 1 MiB，图片上传因 8 MiB 二进制转为 data URL 后会膨胀而单独放宽到 12 MiB；超过上限返回 `413`，畸形 JSON 返回 `400`。这层应用检查不替代 Vercel 自身更低的请求体硬上限，后台仍需在浏览器端压缩图片。
- 踩坑：用查表取值判真做白名单（`if (!STATE_FILES[type])`）挡不住 `__proto__`、`constructor`、`toString`、`hasOwnProperty`、`valueOf`——这些原型键取出来都是真值，会绕过校验并把 `Object.prototype` 当成写入路径送进 GitHub 文件接口。**接口里凡是用对象做白名单，一律用 `Object.hasOwn(map, key)` 判断**（2026-07-26 修复）。
- 编辑或删除文章时必须提交打开文章时返回的 GitHub blob SHA；文件已被其他操作修改时接口返回 `409`，应刷新后重新编辑，不能覆盖较新的内容。
- 站点设置涉及 `_config.yml` 与 `_config.fluid.yml` 时通过单个 Git commit 原子更新；任一源文件版本过期都会拒绝整次更新，不留下半套配置。
- 踩坑：站点设置是用正则改 YAML 文本，两条约束不能省。①**导航名不许含 `"` 和 `\`**——写入用 JSON 转义（`\"`），读回用 `"([^"]*)"`，第一次保存还合法，第二次保存正则会在反斜杠处截断，替换出 `name: "新值"旧尾"`，YAML 解析失败、站点直接构建不出来。所有文本字段另外挡换行与超长。②**改块内字段的正则必须锚定到父块**：`^\s{2}content:` / `^\s{2}name:` 这类写法只是碰巧命中 `footer:` / `about:` 底下那一个，主题配置一旦新增同缩进同名 key 就会静默改错地方，现在统一经 `replaceInBlock` 只在目标块的区间内替换（2026-07-29 修复）。
- `vercel.json` 为全部响应启用 `X-Content-Type-Options: nosniff`，并禁止 `/admin` 与 `/admin/` 被第三方页面嵌入，降低伪装资源执行和后台点击劫持风险。

## 修改网站文字

- 站点标题、副标题、首页标语、页脚、关于页昵称/简介、现有导航显示名：优先通过 `/admin/` 的“站点设置”修改。
- 站点描述、域名、语言、构建目录等底层配置：改 `_config.yml`。
- 导航链接、导航图标、头像、背景图、主题开关等主题配置：改 `_config.fluid.yml`。
- 关于页正文：改 `source/about/index.md`。
- 友链页正文：改 `source/friends/index.md`。
- 留言页正文：改 `source/guestbook/index.md`。
- 文章标题、分类、日期、封面、正文：优先通过 `/admin/` 编辑，也可以直接改 `source/_posts/*.md`。

## 评论（Twikoo）

- 后端为自托管 Twikoo 云函数，`envId: https://twikoo.aoiblog.top`（1.7.x），文章页与留言板共用同一后端。
- 文章页与留言板都走 Fluid 的评论注入点，由 `_config.fluid.yml` 三处开关控制：`post.comments.enable: true`、`post.comments.type: twikoo`、顶层 `twikoo.envId`。三者缺一不显示（`type` 默认是 `disqus`，只开 `enable` 不改 `type` 会加载错插件）。
- **评论 path 由 `scripts/twikoo-path.js` 决定**：它注册 `theme_inject` 过滤器，以同名 `default` 覆盖 Fluid 的 `postComments` / `pageComments` 注入点，path 取 `page.twikooPath || url_for(page.path)`。迁移来的旧文章用 front-matter 里的 `twikooPath`（即旧 `article_id`）读到历史评论，新文章没有该字段就自动回落到真实 URL 路径。
- 留言板（`/guestbook/`）front-matter 写 `comment: true` 和 `twikooPath: "/"`。**注意是单数 `comment`**：Fluid 的 `scripts/filters/post-filter.js` 会在 `before_generate` 阶段用单数 `comment` 重写每个页面的 `page.comments`，写复数 `comments: true` 会被它覆盖成 `false`，评论区直接不渲染。
- 踩坑（2026-07-28 修复）：`_config.fluid.yml` 里曾配置 `twikoo.path: window.location.pathname`，但 Fluid 模板写的是 `path: '<%= theme.twikoo.path %>'`——带引号且转义，线上输出的是**字面量字符串** `'window.location.pathname'`。结果所有文章的文末评论区共用同一个 path 桶，任何人在这里发的评论都会出现在全部文章下。因此 **`twikoo` 段不要再配置 `path`**，交给上面的注入脚本处理。
- 踩坑（2026-07-28 修复）：迁移工具曾给每篇文章正文尾部注入 `<section class="legacy-comments">` 挂载块，与 Fluid 自己的评论区同页并存，导致每篇文章渲染**两个评论区**、两个元素抢用 `id="twikoo"`、两个 Twikoo 版本（CDN 1.6.32 与主题内置 1.6.8）竞争。这些块已随正文清洗一并删除；`source/js/twikoo-legacy-path.js` 只在页面存在 `[data-twikoo-path]` 时才动作，正文清空后它在文章页自然不再生效。
- 踩坑：Hexo Fluid 迁移时 `post.comments.enable` 被置为 `false`，文章页评论一度整体消失；后端始终在线，恢复只需开上述三处配置，无需重建后端。

## 文章阅读页

- 正文排版在 `source/css/aoiblog-post.css`，**所有选择器以 `.post-content` 打头**。该类只出现在 Fluid 的 `layout/post.ejs`，因此样式精确限定在文章页，不会波及同样使用 `.markdown-body` 的关于页/友链页/留言板，也不影响 `/news/` 日报页（日报页根本不加载这份样式）。配色一律取 `aoiblog-home.css` 里的 `--aoi-*` 变量，跟随亮暗两套主题。
- 正文顶层纯文字段落统一使用 `2em` 首行缩进，桌面端与移动端口径一致；选择器只匹配 `.markdown-body` 的直接子段落，并排除包含图片的段落，因此引用、列表、代码块、嵌套组件和图片布局不受影响。该行为由 `npm run test:post` 的样式回归锁定。
- 文章标题在桌面与移动端都静态完整显示；Fluid 的打字效果只从 `post` 范围移除，首页、归档、分类、标签与独立页保持原行为。标题下隐藏固定作者名，继续显示发布日期、字数和预计阅读时长。
- 页面顶沿的细线按 `.markdown-body` 的实际阅读区间显示进度，并在懒加载图片、折叠块等改变正文高度时自动重算；短到不足一屏多的文章不显示。桌面端进入正文后，左右侧栏缩到屏幕边缘；悬停或键盘聚焦侧栏会临时展开，回到文首则完全恢复。低于 `992px` 时不启用侧栏收起。
- 移动目录复用 Fluid 已生成的 `#toc-body`，仅在目录实际包含标题时创建按钮和抽屉。抽屉支持遮罩、关闭按钮、目录跳转和 `Esc` 关闭；打开时将键盘焦点限制在目录内，关闭后把焦点交还给原控件，关闭状态的抽屉不进入 Tab 顺序。初始化必须保持幂等，避免主题刷新后出现重复按钮。
- 代码块移动端默认保持原始缩进并横向滚动，左上角按钮只切换当前代码块的视觉折行，不改变代码文本、复制结果或持久化任何偏好。普通 Markdown 表格使用独立横向滚动容器；语法高亮内部用于排版的表格必须排除，不能套入该容器。
- 方格纸纹只留在正文两侧并降低对比度；文章页新增动效必须响应 `prefers-reduced-motion`。交互逻辑由 `source/js/aoiblog-home.js` 先按日期路径筛选，再以 `.post-content .markdown-body` 确认真实文章 DOM；日期型 404、`source/news/`、`source/admin/` 与普通独立页均不进入初始化。
- 写作时可直接用原生折叠块，无需插件也无需 JS：

  ```html
  <details>
  <summary>折叠标题</summary>

  折叠内容，中间要留空行，Markdown 才会正常渲染。

  </details>
  ```

  注意 `/admin/` 的预览是自制极简渲染器（先 `escapeHtml` 再只认标题/图片/链接/粗体/代码块），折叠块在后台预览里会显示为原文，发布后线上正常。
- 左侧同分类文章列表由 `post.category_bar` 提供。主题默认 `specific: true`，要求每篇文章 front-matter 声明 `category_bar: true` 才显示；本站文章都没有该字段，等于侧栏从未渲染过，因此改成 `specific: false` 对所有文章开启，并用 `post_order_by: "date"` 按时间正序排列以贴合系列阅读顺序。
- 文末版权区展示最后更新时间（`post.copyright.update_date.enable: true`）。该行只在 `updated` 晚于 `date` 时出现，两者相同的文章不显示，属模板的正常行为。
- 旧文正文清洗（2026-07-28，经用户授权的一次性迁移）：迁移自旧 Astro 站的文章正文原本是带内联样式的裸 HTML（`text-indent: 2em`、写死的链接色与图片阴影），会绕过主题变量和暗色模式；同时正文里重复出现与标题同名的 `<h2>` 和 `# 标题`，连同模板的 `<h1>` 构成三重标题并污染右侧目录。已由 `tools/clean-post-inline-styles.mjs` 批量还原为干净 Markdown。该脚本幂等，改写前会把代码与正文分开做逐字比对，任一不一致就拒绝写入并报告。
- 顺带修复：旧文里 `<pre><code class="language-x">` 形式的代码块得不到语法高亮（Hexo 只处理围栏代码块，裸 HTML 的 `<pre>` 原样透传），清洗时已转成围栏代码块。

## 站内搜索

- `_config.fluid.yml` 的 `search.enable: true`，索引在构建时生成到 `dist/local-search.xml`，含全文，无后端依赖。
- **不要安装 `hexo-generator-search`**：Fluid 1.9.9 自带索引生成器（`scripts/generators/local-search.js`，注册名 `_hexo_generator_search`），装第三方插件只会多产出一个用不到的 `dist/search.xml`。主题 `_config.yml` 里那句"基于 hexo-generator-search 插件"的注释已经过时。

## 文章目录（TOC）

- 侧栏目录由 Fluid 内置的 tocbot 渲染，`.toc-body` 超过 `75vh` 时内部可滚动。
- 踩坑：tocbot 默认 `disableTocScrollSync: false`，即高亮项随阅读变化时会自动把目录滚回当前标题，手动向下翻看目录会被反复拽回顶部。已在 `_config.fluid.yml` 的 `post.toc.disableTocScrollSync: true` 关闭该同步（该键经 deep-merge 传入 `tocbot.init`，主题其余 toc 默认不受影响）。

## 发布新文章

推荐方式：

1. 打开 `/admin/`。
2. 输入后台口令。
3. 点击“新文章”。
4. 填标题、日期、分类和 Markdown 正文。
5. 可选上传封面；不上传时使用分类默认封面。上传的封面/正文图会在浏览器端自动缩放（封面 ≤1920px、正文 ≤1600px）并重编码为 WebP 后再提交——因为 Vercel Serverless Function 请求体硬上限为 4.5MB，手机原图直传会被平台以 413 拦掉；压缩逻辑在 `source/admin/index.html`（`compressImage`），GIF 例外（原样上传以保留动画，仅做体积拦截）。
6. 点击“发布”，后台会提交 Markdown 和图片到 GitHub，Vercel 会自动重新部署。

本地方式：

1. 在 `source/_posts/` 新建 Markdown 文件。
2. 图片放到 `source/images/`。
3. 在 front matter 中填写 `title`、`date`、`categories`、`index_img`。
4. 运行 `npm run build` 验证。

## 文档维护

- 当前架构、运行方式、环境变量和日报能力以本文件为准。
- `AGENTS.md` 提供跨编码代理的通用项目规则，`CLAUDE.md` 补充 Claude 专用约束和 skill 入口；二者职责不同、允许独立维护。`docs/workspace_conventions.md` 说明文件分类和命名。
- 完成的实施计划和一次性分析报告不长期保留；有复用价值的结论应并入本文件或对应维护文档。
- `docs/archive/` 只保留仍有兼容、迁移或排障价值的历史记录，阅读时以文件日期为边界。

## 迁移说明

本项目曾使用 `Astro + MongoDB API + public/admin.html` 架构。

2026-06-18 起迁移为 Hexo 静态博客：

- 线上公开 API 返回的 19 篇文章已迁移为 Markdown。
- 后台草稿未迁移。
- 旧 `/articles.html#article_id` 链接由 `source/articles.html` 兼容跳转到新文章地址。
- Twikoo 评论使用每篇文章的旧 `article_id` 作为 path 保留旧评论关联，现由 `scripts/twikoo-path.js` 读取 front-matter 的 `twikooPath` 实现（见「评论（Twikoo）」一节）。**改动或删除文章的 `twikooPath` / `old_id` 会直接断开历史评论。**
- 旧 Astro 前台、旧 MongoDB API 和静态后台不再作为运行入口保留；当前 `api/` 是后来建设的在线后台与日报状态接口。
- 历史迁移工具 `tools/export-articles-to-hexo.mjs` 已于 2026-07-28 删除。它会从早已不是内容真源的旧 API 整体重建并替换 `source/_posts/`，同时重新注入带内联样式的 HTML 和 legacy 评论块，留在仓库里只会把正文清洗成果一次性抹掉。内容真源现在是 `source/_posts/` 加经 `/admin/` 写入 GitHub 的提交；需要查阅该脚本请翻 git 历史。

详细决策见 `docs/archive/2026-06-18-hexo-fluid-migration.md`。

## 每日日报页（/news/）

`source/news/` 是独立的静态"每日新闻驾驶舱"页面，通过导航菜单"日报"访问（`/news/`）。公开页面与生成数据是纯静态文件，`_config.yml` 的 `skip_render: news/**` 保证 Hexo 原样拷贝、不经主题渲染；个人状态文件同时列入 Hexo `exclude` 与 `.vercelignore`，不会进入静态部署。

### 数据管线

- 主管线是 `news-pipeline/daily_news.py`：抓取（RSS / AI HOT / 逐源直连适配器）→ 跨日 URL 去重与重大更新判定 → 预筛 → LLM 初步聚类、分类、五维打分 → 全量同日事件证据归并 → 多条事件凝聚度审计 → 代码合成最终分（含热榜 co-occurrence 公众热度加权）→ 精选与次级集合二次归并、重新审计和选位 → 精选深加工与事实支撑审计 → 生成今日主线、事件追踪、深读推荐、今日论文（HF Daily Papers）、舆论观察、RSS 和搜索索引。最终分夹紧在 5-99：乘数叠加常把原始分推过 99，因此 99 是"顶格档"而非精确分，顶部多条并列 99 属预期、不是评分 bug（2026-07-23 定案，不改公式）。
- 精选展示标题以 30 字为生成软目标，语义完整优先，不按字符盲目截断。模型返回空标题或超过 120 字的异常标题时回退到完整主来源标题；公开 payload 的标题仍以现有来源输入上限 300 字做发布校验，超限报错而不是静默裁剪。该规则在 interim、shadow 和 active 三种客观性模式下保持一致。
- 改新闻源优先改 `news-pipeline/sources.yaml`；调评分、阈值、标签词表、事件追踪、深读、精选长叙述（`detail`）、RSS 和搜索保留窗口优先改 `news-pipeline/config.yaml`。
- **信源接入采用"逐源直连适配器"路线**（参考 AIHOT 的做法：RSS 优先、没 RSS 就直连公开接口/网页内嵌数据，不建万能适配层）。三类接法并存：①标准 RSS（`fetch_rss`）；②自建 RSSHub 实例（Vercel）转 RSS——当前用于科学网、澎湃热门、果壳、Anthropic news/engineering 和财联社·深度等已验证路由，`url` 写占位符 `{rsshub}/路由`，运行时由环境变量 `RSSHUB_BASE` + `RSSHUB_KEY` 拼真 URL（地址密钥不落公开仓库，`resolve_rsshub_sources`，主管线与 `deep_sources` 均支持；未配置则自动跳过）；③专用适配器——`fetch_aihot`（JSON API）、`fetch_thepaper_list`（澎湃频道页 `__NEXT_DATA__` 内嵌数据，各 `list_*` 频道同构可复用）、`fetch_weibo_hot`（genvisitor 访客握手，无需登录/浏览器）、`fetch_bilibili_hot`（公开接口）。**不再扩 RSSHub 路由、不上 Docker**。已关闭的信源线（原因见 `sources.yaml` 尾部终局结论注释）：微信公众号（需常驻中继+人肉续期）、知乎（无登录态全线 4xx）、中青报/界面（JS 壳站）、X 直连（AI 类经 AIHOT 二手接入），以及 2026-07-16 验收停用的 FT 中文网和第一财经。
- **新增信源前必须从 GitHub Actions 出口验证可达性，本地能取不算数**（2026-07-26 实证）：`*.substack.com` 在 Actions 出口被封——`importai` 连续 9 天 0 抓取而同一 URL 本地返回 HTTP 200；同为 Substack 出版物但走作者自有域名的 `interconnects.ai`、`latent.space`、`oneusefulthing.org`、`construction-physics.com` 在 CI 全部成功。因此 Substack 候选一律换自有域名（`importai` 已换 `jack-clark.net`、Noahpinion 用 `noahpinion.blog`），无自有域名者判死。另外两条同期踩坑：接入前先看 feed 最新一篇的日期，停更两三个月的源不进队列；对方 TLS 证书过期或标准 CA 包无法闭合信任链（如 `www.latepost.com`）都是硬阻塞，**不得靠关闭证书校验或私带信任锚绕过**。晚点专用适配器只跟进与配置入口同源、无内嵌凭据的 HTTP(S) 详情链接；列表页给出的跨域或非 Web URL 会被拒绝，不能把上游链接变成服务端任意地址访问入口。
- 主管线在增加任何信源前，必须先观察现有源至少 14 天：抓取成功/零更新、候选与入选量、单源高风险率、独立证据链和来源集中度。`source_health.json` 逐源记录抓取条目、参与评分事件和参与最终精选事件；objectivity shadow summary 记录高风险单源、独立链和来源引用集中度。观察期内不加源、不回填历史数据，数据与人工审查都支持时才可重议。
- 信源分为官方/事实源、分析源、舆论源，并有 T1 / T1.5 / T2 层级。纯舆论源（`source_type: opinion`）支撑的事件分数会封顶在当日有效精选阈值之下，只能进"更多资讯"，也不进入动态阈值账本；有事实源或分析源交叉佐证后才解除限制。
- 抓取健壮性：`fetch_rss`/`fetch_aihot` 统一走 `http_get`（指数退避重试），治 AIHOT 连接重置这类偶发失败——单次请求一挂整源归零。`max_per_source` 默认 18（削减 world/舆论刷屏源的 triage 噪音）；AIHOT 是 AI 深度独木、已精选噪音低，在 `fetch_aihot` 内单独放宽取量、不受该值压制。AI 一手供给以逐篇新闻站（The Decoder 等）为主，不用摘要型 newsletter（每期一条不适配事件聚类）。`source_health.json` 将抓取错误与窗口内零更新分开记录；2026-07-16 验收中，`ftcn` 连续 6 天抓取失败，`yicai` 上游头条接口停留在 2026-05-30，二者均已在 `sources.yaml` 停用。
- 精选采用按产出日等权的动态阈值：每个历史日先对非纯舆论事件最终分计算 nearest-rank P75，再取最近 14 个有效日值的中位数并钳制到 66-82；不足 5 日或账本异常时回退静态 68。五类各有 4 个保留席，优先取过线事件，不足时只从“有效阈值−8”以上补位；`pick_min: 8` 也遵守同一质量线，宁可少发。保留席不参与最终按分截断，精选最多 36 条，供给不足时少发；「更多资讯」仍最多 8 条。次级条目不跑深加工，摘要位只能回退到来源原文：中文原文照登，非中文原文一律留空（`readable_fallback_summary`，按中文字符占比 0.15 判定），不把没翻译的外语原句当成日报自己写的摘要。序列化与审计投影共用同一判定，历史数据不回填；理由与被否掉的翻译方案见 `docs/adr/0009-secondary-items-carry-no-written-summary.md`。可选 `max_per_category` 当前为空，但启用时优先于保留席。AI 与其他类目仍按分竞争，`TRIAGE_SYSTEM` 首轮未改。主题标签只允许来自 `config.yaml` 的 `topic_tags`。
- 同日事件归并使用事件标题、原始标题、摘要和来源作为证据，并要求模型结果恰好覆盖全部输入且索引不重复、不越界。全量事件按最多 40 条的有界基础批次复核；跨批候选优先取共享原始条目或规范 URL 的事件，其余必须共享至少 4 个低频标题/摘要键，再按强制候选、共享键数和稳定索引排序。URL 只代表报道文档而非事件身份，同一篇综合报道可以支撑多个不同事件，因此即使 URL 相同也只送审、不自动合并。初次归并与发布前复核在整次运行中共享最多 20 次模型调用；达到上限后停止付费审计，只合并共享同一原始条目的确定性重复，其余保留并告警。候选对、桥接批次、实际调用、延后批次和预算耗尽状态写入当日质量记录。第一层在评分前复核全部事件，第二层在精选与次级条目拟定后反复执行归并、凝聚度审计和重新选位，直到读者可见集合稳定；分数账本只记录最终结果。同一具体事件只保留一张卡，事实稿与分析稿并入其来源和观点，不同进展仍独立。
- 可信度质量门分两层：同日事件归并后，所有含两个及以上原始条目的事件都会复核凝聚度；审计输出无效或调用失败时，该事件拆回单条、取消多源加成并把证据分降为中性值。精选深加工的模型响应只消费对象行，畸形行会被忽略并让对应事件保留基础内容；随后再核对 `why/context/significance/watch/detail/claims` 是否由当前事件来源支撑。审计失败时保守删除全部扩展字段，只保留标题、摘要、来源、分类、状态、分数和时间等基础内容，避免未经复核的叙述进入日报。
- 面向读者的生成文字（精选 title/summary/why/context/detail 与今日主线）受 prompt 层"客观性规范"约束（2026-07-18 起）：只陈述可追溯事实，媒体的立场性定性必须显式归因（"X 报道称"）、不得写成事实，剥离情绪化措辞与无依据动机推断，禁止为"平衡"编造原文没有的对立观点；立场性判断优先进 `claims`（kind=analysis）。
- 精选深加工按字段分工生成：`summary` 写事实增量，`why` 写公共影响和利害关系，`context` 一个位置承载两种前情——可信延续是轨迹生成的「来龙」，新事件是 enrich 抽取的「起因」，`significance` 给画像相关的学习/行动参考，`watch` 承载「走向」，`detail` 串联来源已有的因果过程和关键细节，`claims` 只承载需要显式归因的分析或不确定判断。起因只抽取不推断，由两道确定性闸门把关：模型必须交出依据的原文片段供精确比对（对不上或系改写即丢弃），起因内出现未归因的推测或动机语气也直接丢弃；拒绝数记在 `cause_evidence_rejected` / `cause_speculation_rejected`。覆盖率因此明显低于放开发布，属刻意取舍，理由见 `docs/adr/0006-cause-is-extracted-not-inferred.md`。走向最多 90 字，需说明 1-2 个关键变量并给出至少一个可观察路标；禁止具体概率、无条件断言和来源外类比，支撑审计删除后不填充占位内容。interim、shadow、active 共用同一字段裁剪策略。prompt 会显式携带 `category`：非 AI 类补必要术语和机构背景，AI 类直接进入增量；机制链、数字比较和利益相关方只在来源支持时选最有价值的一至两项，不为追求深度补写来源外事实。该行为仍使用 interim 摘要输入，五日人工质量验收记在 `docs/news_source_roadmap.md`。
- 踩坑：阶段B（enrich）按 6 条一批发给模型，提示词里只展示本批的全局下标，因此**回填时必须校验 `idx` 落在本批窗口内**，只判 `0 <= idx < len(picked)` 是不够的。放行窗口外的下标意味着一条新闻的返回可以覆盖另一条已经算好的全部读者字段——模型写错下标是这样，抓来的正文用提示注入诱导它写错下标也是这样。更麻烦的是下游 support 审计按事件自己的来源复核，覆盖的后果只表现为 `removed_fields` 无故上涨，查不到源头。越批次下标现在直接丢弃并记入 `enrich_out_of_batch_idx`（2026-07-29 修复）。
- **公开路径当前只到这一层**：`config.yaml` 的 `objectivity.mode` 默认 `interim`，只启用上述 prompt 规则和原有的 support-only 事实支撑审计。完整正文取证、独立证据链佐证、客观性定向修复/降级/降档的代码已经存在，但只在 shadow 或未来的 `active` 模式下运行；**`active` 尚未启用，线上验收尚未完成**。审计模型可用 `config.yaml` 的 `audit_llm` 段单独指定，留空则继承 `llm`。
- 完整模式的证据合同是 `evidence: {basis, publisher_count, independent_chain_count, degraded}`（`basis` 取 `fulltext|mixed|snippet`）；来源可带 `evidence_basis`/`evidence_chain`，claims 用 `sources` 标注归因，`degraded` 表示摘要退化或修复失败后的保守内容，高风险事件复审仍失败会从精选降到"更多资讯"。前端只在结构完全合法时渲染证据概览，旧数据静默降级。正文只是当次运行内存中的审计证据（每源上限 4000 字），不写入日/周报、feed、search、registry、profile、health 或 vocab 等任何数据文件；抓取器不登录、不执行页面脚本、不绕过付费墙，取不到就退回 RSS 摘要。
- 切 `active` 前必须同时通过 7 天线上指标门和 45 条夹具的三轮门，并另行人工评审；安全边界与标签接受集的决策见 `docs/adr/0005-objectivity-label-accepted-sets.md`。DeepSeek 当前运行时的 45 条夹具三轮门已于 2026-07-28 通过（Run #30349424143，最差轮残留红线 0、标签一致性 91.11%、归因 100%、结构 100%），7 天线上指标门与人工评审仍未完成，`objectivity.mode` 保持 `interim`。
- AI HOT 条目会带上其原生分类（模型/产品/论文/技巧）作为 `tag_hint`，在阶段 B 打标时优先入选，保证「研究论文」「技巧观点」这类内容不被大类淹没——前端现有子标签筛选即可单独筛出，无需改前端。
- 兴趣画像影响排序：`interest_profile.md` 非空时，管线对每个事件打"兴趣契合分"换算成分数乘数，幅度由 `config.yaml` 的 `scoring.fit_span` 控制（默认 ±0.30，画像明确不关注的事件被压低、更关注的被抬高）。画像以手动维护 + 低频人工校准为准、蒸馏为辅：页面反馈按钮保留，但反馈输入长期近零属预期状态、不是待修 bug（2026-07-23 定案）。
- 画像含手写的「## 学习参考系」段（长期学习方向/当前能力栈/希望积累的判断力/资讯转化偏好）：阶段B 据此把每条精选的"对我的意义"（`significance`）写成学习路线导向的**可操作参考**（该补什么概念、读什么文档/论文、试什么工具、盯什么能力趋势），无可操作关联则留空。该段每晚蒸馏时由 `split_section` 摘出、绕过 LLM、原样贴回（`update_profile`），不会被自动改写冲掉；旧的「## 我的处境」段仍会被兼容保护。
- 长尾去噪：预筛除丢弃硬垃圾外，还会给"软边角料"（体育赛果、明星八卦、猎奇轶闻、日抛热点）打标；整条来源都是软标记的事件不进"更多资讯"（不影响精选）。"更多资讯"条数由 `secondary_count` 控制（默认 8，真·漏网提醒）。

### 自动运行与本地运行

- GitHub Actions（`.github/workflows/daily-news.yml`）每天 UTC 23:00（北京 07:00 左右）以 `publish` 模式运行，校验通过后自动 commit + push `source/news/data/`，触发 Vercel 部署上线。这是"严禁自动 push"规则的唯一例外，详见 `CLAUDE.md`。例外的边界在工作流里画死：commit 步骤额外要求 `github.ref == 'refs/heads/main'`，并显式 `git push origin HEAD:main`——否则从别的分支手动 dispatch 一次 `publish` 就会把数据推到那条分支上（2026-07-29 收紧）。手动 `Run workflow` 默认是 `validate + shadow_mode:auto`：先把线上数据复制到 runner 临时目录，只运行 generate 并上传临时 artifact，不 commit/push、也不更新 Issue #15；需要连 shadow 验证时显式选 `force`，`skip` 则明确跳过。定时或显式 `publish` 的 `auto` 会读取可信台账：客观性 7 日门或主管线信源 14 日门未完成时继续运行 shadow，两门都完成后自动跳过；状态查询失败时宁可运行受预算保护的 shadow，避免错误终止验收。同一 publish workflow 随后运行云端 `rollout-review`，幂等更新 GitHub Issue #15；完整 `rollout-report.json` 另存为保留 14 天的 Actions artifact。
- GitHub 仓库已启用 Dependabot 漏洞告警与 Secret scanning push protection，并在 Actions 权限层强制第三方 action 使用完整 commit SHA；工作流中的现有 `uses:` 均符合该约束。Dependabot 自动安全更新仍关闭，避免未经人工确认自动创建 PR；`main` 仍不设分支保护，以兼容日报 workflow 和在线后台的既有直写合同。调整这些策略前必须同时评估两条写入路径，不能只按普通应用仓库套用默认保护。
- LLM 配置是 `config.yaml` 的命名 provider：`llm.active_provider: deepseek` 为生产默认，继续显式关闭 V4 thinking；不做自动 provider 切换。两把 key 分别存于仓库 Secrets `STEPFUN_API_KEY` / `DEEPSEEK_API_KEY`，绝不进代码。StepFun `step-explore` 的 Anthropic Messages `/v1/messages` 适配与测试继续保留，但只供人工实验：Run #30346999214 在正常新闻阶段 A 第 2 批触发 HTTP 451 `censorship_blocked`，因此不得作为生产回退。自建 RSSHub 源另需 `RSSHUB_BASE`、`RSSHUB_KEY`。OpenAI 兼容 SDK 的内建重试保持关闭，实际重试次数由管线的 `max_retries` 单独控制；provider 的 `max_tokens` 与连接/读取超时会原样进入请求，避免隐式重试绕过同次运行的预算和失败口径。
- 成本计量：每次运行结束会在日志里按 provider / model / 阶段列出调用次数、输入/缓存命中/输出 token 与折算美元，公开运行把合计写进 `quality-health.json`（`llm_calls` / `llm_input_tokens` / `llm_cached_input_tokens` / `llm_output_tokens` / `llm_cost_usd` / `llm_cost_known`），shadow 合计写进临时 summary。每次实际请求只要返回了 usage（包括随后重试的失败响应）就计入账本；OpenAI 兼容响应同时兼容标准的 `prompt_tokens_details.cached_tokens` 与旧缓存字段，缓存 token 不得超过总输入。相同 provider/model/阶段出现冲突价格、价格缺字段/为负数或非有限值时，成本必须标为 unknown，不能沿用合并顺序中的任一价格；持久化只接受上述 `llm_*` 白名单字段。`cost_guard` 默认在正式生成超过 `$0.06`、shadow 超过 `$0.09` 时发非阻断告警；它们是异常提示，不会为了省钱中止日报。`step-explore` 的 0 只表示当前账号免费授权；未知模型写 `llm_cost_usd: null` 与 `llm_cost_known: false`，不伪装成免费。成本字段不进 `daily/<date>.js`。
- 本地手动补跑（PowerShell）：先运行 `py -3.12 -m pip install --require-hashes -r news-pipeline/requirements.txt`，再按活动 provider 设置 `$env:STEPFUN_API_KEY="你的key"` 或 `$env:DEEPSEEK_API_KEY="你的key"`，执行 `py -3.12 news-pipeline/daily_news.py`。默认产物写到 `news-pipeline/data/`（已 gitignore）；验收时应把 `$env:DATA_DIR` 指向仓库外临时目录，绝不直接写 `source/news/data`。需要抓自建 RSSHub 源时再设置 RSSHub 两个环境变量。
- 两个只在 CI 里设置的可选环境变量，用于把验收证据交给台账，**本地不设即完全不写文件**，不影响日报产出：`ROLLOUT_EVIDENCE_PATH` 让 `generate` 落盘选材/轨迹的 rollout 证据（含每日 enrich 抽样清单，只记条目 id）；`SHADOW_SUMMARY_PATH` 让 shadow 落盘客观性聚合指标 JSON。两者都写到 `runner.temp` / `/tmp` 并作为保留 3 天的 artifact 上传，由 `rollout-review` 下载后喂给 `issue_ledger.py`；都不进 `source/news/data/`，也不含正文或密钥。
- 客观性 shadow：`python news-pipeline/daily_news.py --objectivity-shadow`。它先把当前 `DATA_DIR`（含 feedback/profile/registry/weekly 等状态）整树复制到临时快照，读写只发生在快照里，正常返回、提前返回、异常和校验失败都会还原环境并删除快照；输出只有不含正文和密钥的聚合指标及本次 LLM 用量。Actions 的 shadow 使用 generate 上传的同一份数据 artifact，限时 60 分钟；手动 validate 只有 `shadow_mode:force` 才运行，publish/cron 下仍为只读非阻断、不 commit/push。两项依赖门完成后，工作流用 `accepted` 表示合法跳过：选材把 shadow 依赖视为已满足，客观性和信源计数冻结而非失败。
- 客观性模型验收：`python news-pipeline/objectivity_eval.py`。语料固定为仓库内 45 条夹具（`news-pipeline/fixtures/`，受 canonical JSON 的 SHA-256 约束，不能用 CLI 换），每条先走生产 `enrich` 与完整 audit/repair/fallback，再交独立 judge 评分；生成模型和 judge 都拿不到单条夹具的分类、预期标签和验收阈值。只有活动 provider 的凭证存在才会连跑三轮，并按最差一轮决定退出码；活动 provider 首次 publish 前必须通过残留红线 0、标签一致性 ≥90%、归因 ≥95%、结构 100% 四门。Actions 的 `Objectivity Acceptance` 仅允许从 `main` 手动触发，使用两套 provider Secret 中活动的一套，只读运行并上传保留 14 天的聚合报告，不提交任何数据。
- 顶层 Python 依赖维护在 `news-pipeline/requirements.in`，使用与 Actions 一致的 Python 3.12 在仓库根目录运行 `py -3.12 -m piptools compile --generate-hashes --resolver=backtracking --output-file news-pipeline/requirements.txt news-pipeline/requirements.in`。`sgmllib3k` 使用 `news-pipeline/vendor/` 内受控 wheel，生成后必须保持锁文件中的仓库相对路径并运行一次 `pip install --dry-run --require-hashes`，不能退回会动态下载构建工具的源码包。
- 排查信源抓取时先跑 `py -3.12 news-pipeline/daily_news.py --dry-run`，只抓取、不调 LLM。
- 踩坑：自建 RSSHub 的 `ACCESS_KEY` 是拼在 query 里的，而 requests 的异常字符串会带上整条 URL（或裸主机名）。抓取失败日志一律经 `redact()` 输出，同时盖掉 `key=` 的值、`RSSHUB_BASE` 的完整地址和它的裸主机名。**不能把 GitHub 的 secret 自动打码当作防线**——值一旦被转义或截断，打码就失效，而这是公开仓库的公开日志（2026-07-29 修复）。
- 若通过 `publish.blog_dir` 把独立数据目录同步到博客，管线会完整镜像整个 `data/` 树并清理目标中的陈旧派生文件；切换使用临时目录和备份，失败时恢复旧目录，后续运行也会先恢复遗留备份。只有日报成功生成后才会进入发布同步。
- 发布闸门会解析所有读者可见的来源和深读 URL，只接受带主机名、无空白且端口可解析的 HTTP(S) 地址；只检查 `http://` / `https://` 前缀不够，`https://`、带空格的主机和畸形端口都必须拒绝。生成 RSS 时还会重新校验历史日报：无效条目的 `<link>` 回退到 `/news/`，无效来源不会进入 description 的链接列表，避免旧数据绕过新闸门。

#### 选材与可信轨迹并行上线门

- 每次登记表阶段输出一行「轨迹健康」，稳定记录候选匹配、连续性通过/拒绝、被排除的历史行、整条生成回退、审计字段/claim 回退，以及最终公开走向数/精选数和覆盖率。连续性响应缺失或非法时按拒绝计数，其历史全部计入过滤；生成回退按条目计，审计回退按未采用的字段或 claim 计。
- 离线冒烟夹具是 `news-pipeline/fixtures/trajectory_rollout.json`，固定包含一条可信延续、一条污染历史和一条缺少精确 `item_ref` 的旧行；运行 `py -3.12 news-pipeline/tests/test_trajectory_rollout.py` 不联网、不依赖额外测试包，也不写 `source/news/data/`。常规 `py -3.12 news-pipeline/tests/test_pipeline.py` 会同时执行这组回归。
- 选材改革与可信轨迹已随 PR #16 于 2026-07-22 合并公开，但线上验收尚未通过。本次 36 条/4 席与深读扩充会改变公开样本；活动 provider 切回 DeepSeek 后，2026-07-28 的首次有效 publish（Run #30353163162）产生了新的共享运行时指纹。当前 HEAD 仍包含尚未进入有效 publish 的 LLM 用量计量与发布 URL 校验变更，**下一次有效 publish 会按新共享运行时指纹重新起算全部五门**；2026-07-30 台账的 1/7、1/5、0/5、1/7、1/14 仅是上一指纹的历史快照，不得继续累计。轨迹每天的全量初验复用 `audit_llm` 连接/模型配置并强制 `temperature: 0`；模型、schema 或评审基础设施异常一律记 `needs_review`，留给人工最终确认，不猜测通过。当前逐门状态以 GitHub Issue #15 的幂等台账为准。
- GitHub Issue #15 是**五个门的唯一自动每日台账**（台账 state 版本 `issue-ledger-v2`）。同一北京日期的重跑只幂等更新当日记录，不多算一天；当日任一次发布失败，即使后续重跑成功，当日所有门仍都按失败处理。非发布失败时，`pass` 让对应门 +1，`neutral` / `needs_review` 冻结该门当前计数；`fail` 只清零**连续型**门（选材、轨迹、客观性 shadow），**累计型**门（enrich、信源指标）不清零已攒的有效日，因为缺一天数据不等于观察结果变坏。
- 云端 `rollout-review` 现在一次性给出五门判定，数据来源分别是：选材/轨迹取临时 rollout artifact；客观性 shadow 取 `shadow` job 新落盘的 `shadow-summary` artifact；enrich 安全指标取已提交的 `source/news/data/quality-health.json`；信源指标取已提交的 `source/news/data/source_health.json`。缺任一输入时只记 `needs_review` / `neutral`，绝不推断通过；证据还必须是类型正确、数值有限且内部计数一致的结构，畸形 JSON 值同样按保守状态处理，不能误判为通过。
- enrich 门被拆成两半：机械的 `removed_fields / enrichment_audited_events` 安全指标由台账自动判（超过基线 1.2 倍即 `fail`），其中分母是实际进入事实支撑/客观性审计的读者可见事件数，不能用多来源事件的凝聚度审计数 `audited_events` 代替。历史 interim 记录会从同日 `daily/<date>.js` 的 `stats.pick_count` 补全分母；窗口前不足三个有效新口径记录时只报 `needs_review`。三项文字质量检查仍然只能人工判，因此机械指标未越线也不会自动通过。管线每天按日期确定性地从每个非空类目抽 1 条写入台账（只记条目 id，不复制正文），同日重跑抽到的是同一批；人工复核时用 `Rollout Manual Review` 回填 `samples_passed` / `samples_total`，窗口内累计通过率需 ≥80%。
- 45 条客观性夹具仍由独立的手动 `Objectivity Acceptance` workflow 执行（一次 dispatch 内跑满三轮，取三轮最差值判**四门**：残留红线 0 / 标签一致性 ≥90% / 归因 ≥95% / 结构 100%），不属于每日自动台账。红线只计最终候选中残留的违规；标签一致性测的是 Judge 校准，命中夹具的接受集即算一致；归因与标签均只在结构有效条目上计算，结构失败不再连带扣分。
- `Rollout Heartbeat`（`.github/workflows/rollout-heartbeat.yml`，每日北京 02:00）只做缺口检测：前一北京日期若完全没有台账评论，补一条 `neutral` 缺口行并告警。缺口行**冻结**所有门（既不计入也不清零），因为没跑出日报不等于日报跑坏了。该 workflow 不调用 LLM、不写仓库内容、不关闭任何 Issue。
- Judge 返回额外顶层字段、缺行、重复行、越界编号或非法字段时，轨迹初验会以同一输入重试一次；客观性固定夹具会把非法批次递归拆小，单条仍非法时再重试一次，并用每轮 60 次调用预算限制最坏耗时。重试只修复输出结构，不改变证据、标签、红线或验收阈值。轨迹的确定性失败优先于 `needs_review`；走向低于 80% 时，只有未知项全部转好后仍可能达标才允许人工复核，否则直接失败。
- 台账日期在三个子命令（`sync` / `manual-review` / `heartbeat`）里都按真实日历日期强校验，非 `YYYY-MM-DD` 直接退出。**这不是格式洁癖**：日期会被插进台账条目的 HTML 注释标记，而该评论以 Actions bot 身份发布、被验收门当作可信状态读回；未校验的日期能提前闭合注释并注入伪造的 state 块。`rollout-heartbeat.yml` 在写 `GITHUB_OUTPUT` 前另做一次同样的校验，避免换行伪造后续 step 输出。放宽这条校验等于放弃台账的防篡改性。
- 确需人工裁决 `needs_review` 时，使用只读证据 artifact 复核后手动触发 `Rollout Manual Review`。该工作流只能由 Actions bot 修改同一日期的可信台账，只接受与最新 run ID 和 attempt 一致的 `pass` / `fail` / `neutral`，不能覆盖发布失败或自动确定性结论；公开 Issue 仅记录固定的 `artifact_reviewed` 原因码，不接收或保存自由文本复核说明；后续新 run 或 rerun 会自动使旧人工结论失效。
- 观察期冻结选材运行逻辑和轨迹展示逻辑；必须改动时按影响范围重计。**共享运行时指纹变化会重置全部五门**——样本构成变了，变更前后的证据不得混用；只有轨迹 UI 指纹变化则仅重置轨迹门。自动初验失败、`needs_review` 或台账写入异常只在 Actions/Issue 告警，不阻断日报发布、不改配置、不自动回滚。五门全部达标（含 enrich 内容通过率 ≥80%）时只标记「待人工最终确认」，未达标时列出还差哪几门；任何情况下都不自动关闭 #15、#10、#28 或 #21。
- 每天人工检查全部可信延续，并额外抽查 5 条覆盖不同类目的一次性精选；5 个有效输出日内错误串线、无依据历史/判断、错误延续跳转和主管线发布失败都必须为 0。对全部已展示 `watch` 做质量抽样，至少 80% 同时包含具体关键变量和可观察路标；另记走向覆盖率、轨迹回退率和历史行过滤率，不为提高覆盖率放宽连续性或审计门。
- enrich 五日文字质量门、客观性 shadow 七日门 + 45 条夹具三轮门（DeepSeek 当前运行时的夹具门已于 2026-07-28 通过，shadow 仍在观察）、主管线信源 14 日观察门仍然独立有效，不被选材/轨迹计数替代。共享运行时变更后的首个有效 publish 才是五门的新起点；enrich 安全基线取新窗口前 3 个输出日中位数，客观性固定夹具门随活动 provider 变更重新执行。深读源队列已于 2026-07-26 按实测收缩，现行安排见 `docs/news_source_roadmap.md`：阮一峰数据门已过、只差人工门；Noahpinion 已启用观察；Marginal Revolution 同栏串行接续；晚点虽已续期叶子证书，项目锁定的标准 CA 包仍无法闭合其新 TLS 信任链，继续停用；Apricitas 与 Kyla 因作者停更判死销账。
- 是否回滚由人工根据当日证据决定。轨迹回滚时把 `news-pipeline/config.yaml` 的 `trajectory.enabled` 改为 `false` 后重新生成：连续性验证和登记表兼容更新仍保留，但跳过轨迹生成，公开 payload 标记关闭并移除来龙、走向与延续投影。恢复时改回 `true`；`events.json` 的 v2 可选字段无需迁移或回滚，既有日报数据也不重写。选材参数回退时设置 `pick_dynamic.enabled: false`、`pick_max: 24`、`min_per_category: 2`；保留“保留席不被最终截断”和统一质量下限两个正确性修复，因此这是参数回退，不是恢复旧算法，账本无需迁移。

### 线上数据产物

`source/news/data/` 是线上数据目录，大多数文件由管线或后台 API 创建，不应手工改写，除非下方明确允许。

- `daily/YYYY-MM-DD.js`：每日页面数据。顶层 `quality` 记录审计事件数、拆分数、删除字段数（含 `removed_field_counts` / `removed_field_reasons` 两维分项）、跨日重复数、重大更新数、更新判定失败数、同日事件复核数（`duplicate_audited_events`）、合并数（`same_day_duplicates_merged`）、失败数（`duplicate_audit_failures`）和是否发生降级；同日归并成本护栏另记录候选对数、桥接批次数、实际模型调用数、延后批次数和预算耗尽状态（`same_day_candidate_pairs` / `same_day_bridge_batches` / `same_day_reconcile_calls` / `same_day_deferred_batches` / `same_day_budget_exhausted`）。旧数据缺少这些同日归并字段时继续兼容。`trajectory_enabled` 是当日轨迹展示开关；`themes` 为"今日主线"（2-3 条，每条含 `member_ids` 引用当日 `pick-N`/`more-N` 条目，可跨精选与更多资讯）。每条精选还可带 `context`（来龙）、`watch`（走向）、`significance`（对我的意义，结合兴趣画像生成）、`detail`（中文长叙述，约 300-600 字，由 `config.yaml` 的 `detail` 段控制）和 `claims`（0-4 条需归因的分析或不确定判断，形如 `{text, kind: analysis|uncertain, sources: [来源名]}`，可缺省或为空；读取端继续兼容旧数据的 `kind: fact`）；同 URL 出现实质信息增量时还会带 `is_update: true` 与 `first_seen`，页面明确标注“重大更新”。这些扩展字段只有通过事实支撑审计才会保留。深读条目带 `key_points`（≤3 条）/`audience`/`takeaway`，并可带 `content_type: reporting|analysis|opinion`；非法值或历史数据缺失时前端省略标签。论文条目带 `contribution`/`evidence`/`limitations`/`takeaway`，供详情页渲染。旧数据缺少新字段时前端静默降级。
- `manifest.js`：日报日期清单。
- `quality-health.json`：滚动保留最近 90 天的日报可信度审计统计，并汇总审计事件数、拆分数与拆分率，用于观察错误聚类趋势；`enrichment_audited_events` 单独记录 enrich 内容审计分母，不能用凝聚度审计的 `audited_events` 代替。`removed_field_counts`（按 `why`/`context`/`significance`/`watch`/`detail`/`claims` 分）与 `removed_field_reasons`（按 `evidence_copy`/`audit_unsupported`/`claim_unsupported` 分）把 `removed_fields` 拆成两维，用于回答「详情页的空块是闸门删的还是生成端没写」。两个分项之和必须等于 `removed_fields`，对不上直接阻断发布；这两个键从 2026-07-30 起才有，更早的记录缺失属正常，分析时按有无该键过滤。每日记录同时保留上述同日归并预算指标，以及当次公开运行的 LLM 用量与折算成本（`llm_*` 字段，不含 shadow 运行）。同日重跑会覆盖当日记录。
- `source_health.json`：信源健康度，滚动保留 14 天；保留 `count/error` 区分抓取失败与窗口内无新文章，并记录逐源 `scored_events/selected_events`。某源连续 3 天抓取失败时在 Actions 输出 warning。
- `score_history.json`：动态精选线内部账本（v1），按日期保存非纯舆论事件的最终分，同日重跑覆盖并保留最近 30 个产出日。阈值只读取当天之前的数据；账本损坏或写入失败会 warning 并回退静态线，原子写入不会遗留临时文件。
- `events.json`：跨天事件登记表（v2，兼容读取 v1）。管线先把今日精选与近 14 天活跃事件做候选匹配，再用独立连续性门同时核对具体事件主线、最近可信进展，并逐行验证最近 7 条历史；同类目本身不构成延续，模型声称匹配最近进展时最新历史行也必须验证通过。只有验证通过的旧行参与公开 `day_count/history`，并进入独立批量轨迹生成和轨迹审计；审计只检查新写的 `context/watch/claims`，字段拒绝时退回当天已经审计的精加工内容，不改变精选层级；整条生成或审计失败时则按一次性事件展示，不输出来龙或延续入口。旧 `watch` 与证据足够时，来龙可用 `兑现/部分兑现/未兑现/反转` 回对上一期走向；证据不足不输出结论。历史行保存轨迹审计后的最终 `watch`、来源标识和 `日期:item_id` 引用，旧行缺少这些字段时仍可读取。同日重跑优先按稳定条目引用替换当日行，即使首日标题修正也保留 `event_id`。整次登记更新先在内存完成；`daily/YYYY-MM-DD.js`、`manifest.js` 和 `events.json` 作为同一可回滚事务替换，任一文件替换失败都会恢复三者旧版本，RSS、搜索索引和质量记录只在事务成功后更新。7 天无新进展自动归档，归档超 60 天删除，文件缺失或损坏时冷启动重建。
- 事件线**身份名只在首次出现时确定**，续接不再用当天标题覆盖它——当天标题仍完整记进 history 行。旧数据中被覆盖过的名字已一次性回填为首日标题（408 条中 56 条）。
- 事务收尾会做一次**跨天事件线归并**（`reconcile_stale_event_lines`）：候选门要求同类目、日期区间重叠，**且共享至少 8 个低频标题/摘要键**，再进有界批次，由独立 LLM 审计按「是不是同一件事」而非「是不是同一主体」划分，复用同日归并的召回键、并查集与全划分校验。只用「同类目+区间重叠」远远不够——一张跨越数周、只有五个类目的登记表里几乎每对线都满足它，实测会把 408 条中的 406 条每天全量送审；加上键阈值后降到约 31 条。阈值 8 由实测标定：真正的碎片线共享 28-46 个键，噪声对绝大多数只共享 0-3 个。**只处理今天没有写入的线**——今天的线携带回填进日报条目的 `event_id` 和连续性门判定，动它等于推翻已独立验证的结论；今天新建的碎片会在它不再收到精选之后的某天被并掉。审计失败或回复不是完整划分即整批不合并并标记质量降级（漏并只留下两条线，误并毁掉事件身份）。合并以 `first_seen` 最早者为身份，history 按日期去重并保留身份线自己那行，`pinned` 与 `active` 只要有一条成立就继承。详见 `docs/adr/0007-event-lines-merge-across-days.md`。
- `feedback.json` / `read_later.json` / `favorites.json`：由 `api/newsState.js` 写入，分别保存反馈、稍后读和 ⭐ 收藏状态，各封顶 1000 条。稍后读/收藏按 `item_id + date` 去重；收藏只存 `date + item_id` 引用（外加 title/category/url 兜底字段，url 可缺省），收藏页凭引用从 `daily/*.js` 重渲染完整卡片，管线暂不消费 favorites。反馈支持删除式撤销：payload 带 `op: "remove"` 时删除最后一条同 `date + item_id + action` 的记录（页面「更多类似」再点一次即撤销）；管线当晚已蒸馏进画像的部分不回滚，需手改 `interest_profile.md`。
- `interest_profile.md`：兴趣画像，管线会把 marker（`<!-- last_feedback_ts: ... -->`）之后的新反馈蒸馏进去。这个文件可以人工编辑或删行（也可一次性手写丰富的种子画像），但偏好要写成以 `- ` 开头的要点。画像既影响精选排序（兴趣契合分），也用于生成每条精选的"对我的意义"。
- `deep_seen.json`：深度阅读推荐 URL 去重记录，按配置保留。
- `deep_health.json`：最近 14 天深度阅读健康度（v2），按源区分抓取成功/失败、窗口内抓取量、去重后候选、已评分、主题匹配、过线和入选；即使当日零候选也会留记录，避免把低频源误判为失效源。
- `misses.json`：仅个人签名会话可通过 `api/newsState.js` 读写的漏读记录，字段固定为 `id/ts/date/title?/url?/reason`；`date` 必须是真实的 `YYYY-MM-DD` 日历日期，标题或有效 HTTP(S) URL 至少一个，`reason` 只取 `important_event`、`deep_read`、`missing_perspective`，最多保留 1000 条并可撤销。页面分别显示为“重要事件”“值得深读”“缺少视角”。文件不进入画像、评分或信源调整。
- `feedback.json`、`read_later.json`、`favorites.json`、`misses.json`、`vocab-book.json` 与 `interest_profile.md` 通过 Hexo `exclude` 和 `.vercelignore` 排除在静态部署之外，线上 `/news/data/` 不应直接提供这些文件。它们仍以公开 Git 仓库文件为存储后端（尚未产生的文件除外），因此不得写入秘密、隐私正文或可识别个人身份的信息；若需要真正的私密状态，应迁移到私有存储，并清理已经提交过的内容及 Git 历史。
- `papers_seen.json`：今日论文（HF Daily Papers）推荐去重记录，按 `config.yaml` 的 `papers.seen_keep_days` 保留。
- `vocab/YYYY-MM-DD.js` / `vocab-book.json`：**单词本功能已于 2026-07-10 停用**（`config.yaml` 的 `vocab.enabled: false`，管线不再每日挑词；前端界面已移除）。历史数据文件与 `api/vocab.js` 接口原地保留，想恢复时把 enabled 改回 true、前端从 git 历史找回单词本界面即可。
- `feed.xml`：RSS 订阅文件，地址为 `/news/data/feed.xml`，按 `config.yaml` 的 `feed_days` 收录精选，深读推荐带【深读】前缀。来源 URL 的协议校验放在发布闸门 `validate_daily_payload`（必须匹配 `^https?://`），不是放在渲染端：前端 `safeUrl` 挡得住页面，但 feed 的 `<item><link>` 是原样输出给阅读器的，闸门 fail-closed 才不用指望每个消费端各自兜底（2026-07-29 补齐）。
- `search_index.js`：站内搜索紧凑索引，缺失时可由管线从历史 daily 文件重建。
- `news-seen/YYYY-MM-DD.json`：普通新闻跨日去重账本，按日分片并滚动保留 90 天；同 URL 仅时间戳刷新时会在进入任何当日视图前过滤，标题或摘要变化后才交给模型判断是否为重大更新。账本缺失或损坏时从 `all/` 历史档案恢复，且只在日报通过发布校验后写入当天分片。
- `all/YYYY-MM-DD.js` + `all/manifest.js`：全量轻档——抓取窗口内通过跨日去重的全部条目轻字段（标题/链接/来源/类别/时间），滚动保留 90 天。评分阶段结束后 `backfill_all_scores` 按 URL 把事件分回填到匹配条目（被预筛砍掉的无分）；payload 带 `min_score`（`config.yaml` 的 `all_view_min_score`，默认 40），前端默认只显示达标条目、可切换显示全部。两步均独立故障域，失败只记日志、不阻断主管线。

### 页面能力

- 新闻页是无前端框架、无打包步骤的原生 ES Modules 页面：`source/news/index.html` 只保留语义骨架，样式位于 `source/news/news.css`，路由、数据加载、视图和个人操作拆在 `source/news/js/`。现有 `window.NEWS_*` 全局数据脚本继续兼容；数据加载器只接受真实的 `YYYY-MM-DD` 日报日期和 `YYYY-Www` 周报编号，避免 URL 参数被解释为任意脚本路径。
- 页面采用共享响应式外壳：桌面端使用固定左侧栏承载站点标识和 **时间线**、**全部动态**、**报告**、**档案**主导航；移动端使用站点栏、横向主导航和报告归档栏组成的多层顶部导航。裸地址和未知视图默认进入 manifest 最新一期日报；有效个人会话下追加 **收藏**，并显示全局稍后读入口。规范路由为 `?view=timeline`、`?view=all`、`?view=reports&period=day&date=YYYY-MM-DD`、`?view=reports&period=week&week=YYYY-Www`、`?view=topics`、`?view=favs`，旧 `view=picks/day/week` 地址会自动映射。未登录用户直达收藏路由时保留 URL 并显示登录提示，不回退或伪装成时间线。跨天条目统一使用 `日期:id` 复合引用键，反馈、收藏、稍后读和主题追踪按条目或事件最近出现日期记账。
- 新闻页虽然不继承 Fluid 导航，但始终保留博客出口：桌面端左侧栏底部显示“← 返回博客”，移动端站点栏显示首页图标，均以普通 `href="/"` 在当前标签页返回博客首页。该链接不带 `data-route`，避免被日报内部客户端路由接管。
- 时间线视图：按发布时间连续倒序呈现不折叠的单列时间轴，以北京时间日期节点分隔，日期统一显示为中文月日与星期，今天和昨天增加相对前缀；条目按原文发布时间转换为北京时间后归日，日报文件日期只代表生成批次，无有效发布时间时显示「时间待确认」。跨天事件有实质新增时保留在原时间位置并标「延续」，纯重复报道合并来源。顶部「本期优先读」只展示最新一期精选，排序时可聚合近 3 期同事件的独立信源，并结合分数和 36 小时时间衰减选出最多 3 条；它不是归拢多条精选的「今日主线」。页内检索与普通时间轴采用相同归日和去重口径。
- 全部动态视图：按日期节点使用倒序单列时间轴，提供文本搜索、来源筛选、分类筛选和评分过滤。回填评分的日子默认只显示 `score >= min_score` 的条目，并提示已隐藏条数，可切换显示低分或未评分内容；条目同时展示来源、分类和分数。最新一天里已进精选的条目加「✓ 已进精选」徽标并淡化（补漏网时眼睛可直接跳过），旧日期不标——那时的「已进精选」你已记不得读没读过。该标记是渲染完成后的异步装饰，**整页渲染绝不等待日报文件**：全部动态页不依赖日报是否可用、是否够快。
- 报告视图：桌面端显示日/周切换与归档控制栏；移动端顶部栏横向排列周期、归档和前后日期控制。日报正文按 AI、互联网/科技、财经、社会、国际五类稳定分节并全部展开；今日主线后提供仅含非空类目的报告内跳转，隐藏或恢复精选时同步更新。日报和时间线卡片直出摘要、「为什么重要」，并仅在 `watch` 存在时追加「走向」。可信延续在日报卡片显示可聚焦的「第 N 天·延续」链接：优先跳到上一条精确详情，旧历史缺少 `item_ref` 时降级到对应日期的日报。前情、对我的意义和 claims 只在详情页展开：`context` 一个槽位按来源分栏名，可信延续显示「来龙」，新事件显示「起因」；若可信延续的 `context` 以格式完整的「走向回对」收尾，详情页把它独立显示并保留文字状态，其他形状原样降级。「追踪中」紧跟新闻分节，深读、论文、舆论观察和更多资讯依次置后。刊头按 300 字/分钟显示当前可见核心日报估时，口径为导语、最多 3 条今日主线以及未隐藏精选的标题、摘要、为什么重要和启用中的走向；不读取顶层 `read_minutes`，也不含详情页字段。追踪、深读导读、论文、舆论和更多资讯合并显示附栏导读估时，深读标题仍单独汇总入选原文估时。30 分钟只是通读日报并选择性阅读深读的软目标，不据此裁剪内容。有效个人会话可在刊头下补记遗漏，表单明确提示记录会进入公开仓库；周报增加所选自然周近 7 天遗漏清单与原因汇总，普通访客不加载或显示该状态。
- 档案视图（所有访客可见，URL 仍为 `/news/?view=topics`，路由键不改以免破坏既有链接）：定位是历史检索工具，不是每日通读的一部分。首屏是「题材地图」，紧凑自适应网格陈列受控标签、精选条数与该题材最新一条精选的日期；**按总量排序而非活跃度**——检索靠位置稳定的肌肉记忆，按活跃度排会让卡片每天换位。点击进入对应 `tag:` 时间线。下方「事件线」把 📌 追踪中置顶，其余不分进行中/归档、按最新日期倒序排成一列（检索时并不知道目标是哪种状态，分组等于要在两组里各找一遍），已归档只在卡上给灰色小标。卡面直出最新一条进展和「起止日期 · 跨 N 天」，展开才看全链；有效个人会话下可追踪或取消追踪。
- 全站历史搜索在桌面端常驻内容工具栏；移动端由顶部搜索按钮打开全屏覆盖层，支持关闭按钮与 `Escape` 返回触发按钮。
- 页面视觉采用暖纸色上的报刊编辑风，亮/暗跟随博客：初始化读 Fluid 写入的 `localStorage["Fluid_Color_Scheme"]` 决定亮暗，未设置则跟随系统。阅读型日报、周报、时间线和详情页统一使用 780px 阅读栏；正文条目以栏线分隔，今日主线、深读和结论使用双线特稿框。日报刊头的导语是页面唯一 `h1`，日期使用 `<time datetime>`，装饰印章不进入无障碍树；期号按日报日期的年内日序生成 `YYYY · 第DDD期`，不依赖 manifest 数量。supplementary 栏目通过内部 `data-kind` 区分版式，仅在正文容器达到 740px 时让追踪、论文和更多资讯启用双栏，深读和舆论观察始终单栏。五类颜色仅用于分类文字和栏目题花，事实状态继续使用独立语义色。新增装饰统一使用 `--ink`、`--vermilion`、`--rule` 等 token，暗色模式只覆盖 token。耦合点：博客若更换主题或改这个存储键，日报页暗色会静默失效。
- 视觉回归基准位于 `docs/visual-baselines/news-editorial/`，覆盖时间线、日报、周报、详情、全部动态、档案和收藏七种状态，各保留 1440px 亮色与 390px 暗色截图。它们用于人工对比版式，不参与运行时加载。其中 `topics-*.png` 拍摄于档案页改版之前（仍是三段分组 + 底部题材地图的旧版式），下次改动该页时一并重拍。

#### 新闻页衬线字体

- `source/news/fonts/noto-serif-sc-700/` 是 Noto Serif SC Bold 2.003 的高频字子集，只用于刊头、标题、栏目名和数字；字符清单由已提交新闻 UI 与日报/周报语料中频率最高的 600 个汉字、ASCII 和常用标点组成，子集外字符回退到系统宋体。完整 WOFF2 冷传输为 433,508 字节。源字体来自 Noto Serif CJK 官方 `Serif2.003/14_NotoSerifSC.zip`，`NotoSerifSC-Bold.otf` 的 SHA-256 为 `24693D48BDB9152F0A06B02AF625638A1097ABD6DE4010EBBA027F6E82710527`。OTF 不入库，分发目录保留 `OFL.txt`。
- 再生成时先在固定仓库状态运行 `node tools/font-subsets/build-news-serif-chars.cjs`，再在临时目录安装固定版本 `cn-font-split@7.4.3`，把其 `node_modules` 放入 `NODE_PATH`，然后运行 `node tools/generate-news-font.cjs <NotoSerifSC-Bold.otf> tools/font-subsets/news-serif-sc.txt source/news/fonts/noto-serif-sc-700`。生成后复制官方 `LICENSE` 为输出目录的 `OFL.txt`，并删除工具生成的 `index.proto`。该版本 CLI 的重复 `--subsets` 参数在 Windows 上存在解析问题，因此使用同版本 Node API；脚本显式结束一次性进程以避开生成完成后的 FFI 清理崩溃。
- **统一详情页**与各列表视图共用同一套导航、搜索、主题切换和稍后读外壳，路由使用 `/news/?date=YYYY-MM-DD&type=news|deep|paper&item=<id>`，旧式无 `type` 链接仍按 news 兼容。新闻详情在标题下先给一行元信息（北京时间发布时刻 + 分类）和一条置顶「阅读原文」（取首个事实源、显示域名），接着把摘要作为无标题导语直出（与深读/论文同形），正文区再按**事实先行**的「来龙 → 正文 → 为什么重要 → 走向 → 对我的意义」组织，缺失段落静默省略。摘要不占章节标题但必须始终显示——搜索视图、周报「本周值得读」和卡片「第 N 天·延续」这三条入口进详情页时读者没见过卡片，且「更多资讯」条目只有摘要没有正文，去掉就是纯丢信息。之后呈现证据概览、claims，末尾用「相关链接」区块逐行列出全部来源（来源名 + 类型标记 + 域名，事实源排在分析源和舆论源之前），再接操作区；深读呈现推荐理由、核心观点、关键点和适合读者；论文呈现阅读理由、研究结论、贡献、证据与局限。缺少新字段的历史数据按现有字段静默降级，有效个人会话下保留稍后读、收藏与新闻反馈操作；「更多资讯」同时提供原文与站内详情入口。RSS 继续读取 `watch` 字段并以「走向」标注。
- 浏览器通过不可由 JavaScript 读取的签名会话判断是否显示个人操作；普通访客看到的仍是纯阅读页。高权限后台口令不会持久化，也不会发送给日报接口。
- 反馈包括不感兴趣、更多类似、来源质量低、追踪/取消追踪。个人新闻卡直接展示不感兴趣与收藏，稍后读、更多类似、追踪和来源反馈收进原生溢出菜单；深读与论文直接展示收藏、把稍后读收进溢出菜单。日报、时间线、详情和收藏复用同一操作布局，来源质量低仍会在后续管线运行中按近 90 天反馈自然日机械降权，不修改 `sources.yaml`。
- 卡片上的稍后读、更多类似、追踪都是可撤销开关，再点一次即撤回对应记录；操作移入菜单不改变 API、localStorage 键或同步语义。个人操作先做乐观展示，服务端写入失败时会同时回滚内存、localStorage 与卡片状态；取消追踪保留显式的 `false` 覆盖，使当前报告的「追踪中」区立即移除该事件，不能因日报静态数据仍为真而反弹。
- ⭐ 收藏（仅个人会话）：独立于稍后读的永久精华库——稍后读是待读队列（读完沉底），收藏是"觉得最有价值就存"。精选、深度阅读、今日论文三类卡片上都有 ⭐ 按钮（再点取消）；收藏页按收藏时间倒序使用单列阅读流，并提供全部、新闻、深读、论文类型筛选。条目凭 `date + item_id` 引用从对应 daily 文件懒加载并重渲染完整卡片，跨天引用沿用 `日期:id` 复合键；服务端列表会并入本地高亮缓存（`news_fav`，永久不清理），换设备后卡片 ★ 状态一致。
- 追踪事件即使不进精选，也会出现在页面的追踪区；管线会用"更多资讯"补匹配，尽量防止断档。
- 深度阅读频道独立于新闻主管线，源来自 `sources.yaml` 的 `deep_sources`，每个源归入 `ai_engineering`、`tech_business`、`society_finance` 三栏（旧配置名 `zh_society_finance` 仍可读，新数据只写新名）。前三席优先从三栏各取一篇过线文章，空栏名额按总分释放；第四席取剩余最高分，最多 4 篇且不降低 7 分门槛。深读不另建 `voices` 栏，体裁由可选的内容类型标签表达。`deep_sources.type` 可切换专用适配器；综合评论源可用 `topic_filter: finance` 仅保留宏观、商业、市场、劳动和公共经济政策文章。深读失败只丢当天深读推荐，不影响新闻日报产出。
- 今日论文频道同样独立于新闻主管线：抓 **Hugging Face Daily Papers**（社区精选 + 点赞，公开接口无需 key），LLM 按 `interest_profile.md` 的学习坐标（前端/全栈/AI 应用/自动化）从当天几十篇里挑 3-4 篇，产出中文标题、"该读什么/该补什么概念"，带点赞数与"是否有开源代码"标记。写进 daily js 的 `papers` 字段，前端日视图「今日论文」板块渲染（紫色左边框区别于深读）。论文不是新闻——不进精选评分、不占五类名额。参数在 `config.yaml` 的 `papers` 段（`enabled`/`lookback_days`/`max_candidates`/`pick_threshold`/`pick_max`/`seen_keep_days`），失败只记日志、不阻断每日产出。
- 舆论观察：微博/B站热榜（`sources.yaml` 的 `pulse_sources`，直连公开接口）只作两个用途，热榜词条本身永不成为新闻条目——①`opinion_pulse` 用 LLM 挑 2-3 个值得说的传播现象，讲"为何热/群体情绪/平台机制"（滤纯明星八卦），写 daily js 的 `opinion` 字段，前端「舆论观察」板块渲染（琥珀色左边框）；②co-occurrence 暗排序：热榜词条与真新闻事件文本重合（4 字连片或二元组覆盖 ≥0.5）时，该事件最终分乘 `opinion.cooccur_bonus`（默认 1.08）。参数在 `config.yaml` 的 `opinion` 段；热榜抓取或 LLM 失败只丢当天舆论板块，不阻断日报。
- 周综述按周一至周日的自然周生成：主管线每次日报运行都会幂等检查最近一个已结束周，覆盖至少 **5/7** 天且报告尚不存在时才合成，低于门槛则跳过；报告会列出覆盖期数与缺失日期。新版静态数据为兼容型 v2，包含周主线、数字盘点、3-6 个动态主题、代表报道复合引用（`date:item_id`）、上周判断回收、下周信号，以及单列的深读/论文引用；写入前会校验全部引用存在。旧周报不改写，低于 5/7 的旧报告不进入新版归档。**失败只记日志、不阻断每日产出，也不进发布校验**；不新增 workflow。

### 验证与移除

- 管线快速回归：`py -3.12 news-pipeline/tests/test_pipeline.py`。完整 Python 回归：`py -3.12 -m pytest news-pipeline/tests -q`，其中包含跨批同日归并、发布事务和全部历史日报引用完整性检查。测试不调 LLM、不联网；改评分、聚类、可信度审计、健康度、事件登记、偏好学习、深读、周综述、RSS 或搜索索引逻辑后必跑完整回归。
- 客观性回归：`py -3.12 news-pipeline/tests/test_objectivity_audit.py`（证据合同、审计/修复/降级、夹具完整性、删除字段分项守恒、次级回退摘要判定与序列化/审计投影一致性）与 `py -3.12 news-pipeline/tests/test_shadow_rollout.py`（shadow 快照隔离与环境还原）。两者同样不调 LLM、不联网，静默通过、失败非零退出；改客观性审计、证据结构或 shadow 流程后必跑。
- 新闻页回归：`npm run test:news`。测试使用 Node 内置测试器与 jsdom，覆盖新旧路由、DOM 渲染、个人操作 API 合同、无障碍状态和空数据降级；修改 `source/news/index.html`、`source/news/news.css` 或 `source/news/js/` 后必跑。
- 完整交付前运行 `npm run build`，确认 Hexo 能把新闻页 ES Modules、样式、字体和静态数据原样输出到 `_config.yml` 指定的 `dist/news/`，并确认 `dist/admin/` 仍存在。
- 移除方式：删除 `source/news/`、`news-pipeline/`、`.github/workflows/daily-news.yml`、`_config.yml` 中的 `- news/**`、`_config.fluid.yml` 菜单中的 `news` 项即可完全剥离。
- 历史沿革：管线原为独立项目 `D:\每日新闻网站`，已在 2026-07-04 迁入本仓库并退役。
