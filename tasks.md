# Astro 迁移任务清单 (Tasks)

- [ ] **Task 1: 初始化 Astro 项目环境**
  - 在当前项目根目录执行 `npm install astro` 并初始化必要文件。
  - 创建 `astro.config.mjs` 基础配置。
  - 更新 `package.json` 中的 `scripts` (`dev`, `build`, `preview`)。

- [ ] **Task 2: 迁移静态资源及管理后台**
  - 创建 `public/` 目录。
  - 将 `admin.html`、`style.css`、`script.js` 和 `images/` 移动至 `public/` 目录下，确保其独立性和相对路径访问。

- [ ] **Task 3: 提取通用基础组件 (Layout & UI)**
  - 在 `src/layouts` 下创建 `BaseLayout.astro`，封装 `<head>`、全局样式引用及页面骨架。
  - 在 `src/components` 下创建 `Header.astro`，实现顶部导航及主题切换按钮。
  - 创建 `Footer.astro` 和 `FloatingMenu.astro`，实现底部版权、社交链接和悬浮操作功能。

- [ ] **Task 4: 重构首页 (index.astro)**
  - 创建 `src/pages/index.astro`。
  - 拆分首页的“最新文章”、“知识专栏”、“关于我”、“留言板”和“友情链接”模块，作为子组件。
  - 迁移并保留首页内联的 JavaScript 脚本（负责调用 `/api/getArticles` 和动态渲染）。

- [ ] **Task 5: 重构文章页 (articles.astro)**
  - 创建 `src/pages/articles.astro`。
  - 接入原有的 Markdown 解析 (`marked.js`) 和代码高亮 (`Prism.js`) 逻辑。
  - 保留文章列表与文章内容的 SPA (单页应用) 交互模式。

- [ ] **Task 6: Vercel 配置与 API 适配**
  - 审查并更新 `vercel.json`，确保不再干扰 Astro 的默认构建路由（移除过时的 `@vercel/static` 配置）。
  - 保留 `@vercel/node` 或依赖 Vercel 的原生 API 路由处理，确保 `/api/*` 接口能够被正确拦截执行。

- [ ] **Task 7: 本地环境测试**
  - 运行 `npm run dev`，检查前端页面显示和交互（特别是移动端响应式布局）。
  - 访问 `http://localhost:4321/admin.html`，验证管理后台是否能正常加载。
  - 验证 API 接口是否正常获取文章数据，图片资源是否加载成功。

- [ ] **Task 8: 生产部署验证**
  - 提交代码并触发 Vercel 构建（可能需要在 Vercel 面板将 Framework Preset 切换为 Astro）。
  - 线上复测文章数据拉取、后台文章发布、图片上传及路由跳转等全链路功能。
