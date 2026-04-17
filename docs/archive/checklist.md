# Astro 迁移验收清单 (Checklist)

- [ ] **后台无损验收**
  - [ ] `/api` 目录及内部的所有 `.js` Serverless Function 保持原样，未经修改。
  - [ ] 通过 `http://localhost:4321/admin.html`（或部署后域名）访问后台管理界面无报错。
  - [ ] 后台依然能成功调用 Vercel API 保存文章至 MongoDB。
  - [ ] 后台依然能成功调用 GitHub API 上传图片并展示。

- [ ] **静态资源与样式兼容**
  - [ ] `public/style.css` 能够被 Astro 的新页面及 `admin.html` 正常引入并渲染。
  - [ ] `public/script.js` 逻辑（主题切换、动画等）能够正常运行，无 `undefined` 或 DOM 元素未找到错误。
  - [ ] 原有 `images/` 目录内的所有历史图片（如 `img_xxx.png`）都能正常访问（路径：`/images/xxx`）。

- [ ] **页面重构与数据渲染**
  - [ ] 首页 (`index.astro`) 正常渲染结构，页面头部、底部、主体内容排版未乱。
  - [ ] 首页能够正常拉取 `/api/getArticles` 数据并生成最新文章列表和动态知识专栏。
  - [ ] 首页轮播字幕、悬浮菜单及“关于我”区域等交互均正常。
  - [ ] 文章页 (`articles.astro`) 正常渲染结构，保留原有的侧边栏（文章列表 + 搜索筛选）、中间文章区、右侧 TOC 大纲区。
  - [ ] 点击文章列表，右侧正文区能够通过 `marked.js` 正常渲染 Markdown 内容，且标签不被破坏（HTML 兼容）。
  - [ ] 文章内容中的代码块能够被 `Prism.js` 正常高亮并带有行号。

- [ ] **第三方服务接入**
  - [ ] 首页留言板区域的 Twikoo 评论系统 (`https://twikoo.aoiblog.top`) 能够正确加载和展示历史留言。
  - [ ] 文章页底部的 Twikoo 评论系统能正确加载，并根据文章路径隔离评论数据。

- [ ] **构建与部署配置**
  - [ ] 验证更新后的 `vercel.json` 不会导致 404，也不与 Vercel 原生的 Astro 构建冲突。
  - [ ] 线上环境下的静态资源路由 (`/admin.html`、`/style.css`) 未被拦截或重写为 `index.html`。
  - [ ] Vercel 生产环境中的 MongoDB 连接数正常（保留连接复用机制的 Core Memory）。
