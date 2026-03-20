# 个人博客项目演进与技术架构记录

本文档用于记录当前个人博客从初始创建到后续优化的完整演进过程，以及项目所采用的核心技术栈与架构设计。

---

## 🏗️ 核心技术栈与架构概览

本博客采用**无后端（Serverless）静态架构**，将静态资源托管、云端数据存储与第三方服务无缝结合，实现了极低成本（甚至零成本）且易于维护的部署方案。

### 1. 技术选型
- **前端核心**：纯原生 HTML5, CSS3 (CSS Variables), Vanilla JavaScript (原生 JS)
- **数据交互**：Fetch API
- **部署与托管**：GitHub Pages (静态站点托管)
- **内容存储**：GitHub 仓库 (`articles.json` 充当云数据库)
- **评论系统**：Twikoo (基于 Vercel 部署服务，数据存储于 MongoDB Atlas)

### 2. 系统架构设计
- **前端页面展示**：用户访问 GitHub Pages 托管的静态页面。
- **文章数据流转**：
  - **前台读取**：通过 JS 动态调用 GitHub API 读取根目录的 `articles.json` 渲染文章列表和内容。
  - **后台管理**：通过 `admin.html` 页面输入 GitHub Personal Access Token 进行鉴权，利用 GitHub API 直接对 `articles.json` 进行增删改查（CRUD）操作，并支持直接上传图片到仓库。
- **评论数据流转**：前台页面嵌入 Twikoo 脚本，将评论数据直接读写至部署在 Vercel 上的 Serverless 接口，最终落盘到 MongoDB Atlas 云数据库。

---

## 🚀 项目演进与修改记录

### 阶段一：基础架构搭建与无后端改造
1. **静态页面开发**：完成了 `index.html` (首页)、`articles.html` (文章阅读页)、`admin.html` (后台管理页) 及配套的 `style.css` 和 `script.js`。
2. **废弃本地 Node.js 后端**：为了实现完全的静态化部署，移除了早期的本地 Node 服务。
3. **集成 GitHub API**：
   - 改造 `admin.html`，实现基于 `localStorage` 缓存 Token 的安全鉴权机制。
   - 实现了基于 Base64 编码的 `articles.json` 远程读写功能。
4. **Git 与部署**：将项目推送到 GitHub，配置 GitHub Pages 进行自动化静态托管。
5. **评论系统接入**：放弃 LeanCloud，转为在 Vercel 部署 Twikoo 服务并连接 MongoDB Atlas，解决跨域与数据库 IP 白名单问题（放行 `0.0.0.0/0`）。

### 阶段二：UI/UX 深度优化与阅读体验提升
基于现代优秀博客（如 labuladong）的设计理念，在**不改变现有纯前端架构**的前提下，进行了平滑升级：

1. **暗黑/护眼模式 (Dark Mode)**
   - 在 `style.css` 中引入了原生的 CSS 变量（`--bg-color`, `--text-color` 等），重构了硬编码的颜色值。
   - 在所有页面的导航栏（包括 `index.html` 首页与 `articles.html` 等子页）新增 🌞/🌙 切换按钮。
   - 利用 `localStorage` 实现主题偏好的持久化记忆，并在各页面的 `<head>` 中注入初始化脚本以防止页面刷新时出现“白屏闪烁（FOUC）”。
   - 修复了导航栏在暗黑模式下向下滚动时，背景色被 JavaScript 强制覆盖为白色的 Bug，实现了滚动监听与主题切换状态的实时完美同步。
2. **三栏布局与动态大纲 (TOC)**
   - 将 `articles.html` 从双栏布局升级为经典的“左导航 + 中内容 + 右大纲”的 `300px 1fr 250px` 三栏布局。
   - 优化了布局容器，取消了原有的最大宽度限制（`max-width`），改为 100% 全屏宽度（仅保留左右边距），为中间的阅读区留出了极致宽广的空间。
   - 编写 JS 脚本 `generateTOC()`，在文章渲染后动态提取正文中的 `<h2>` 和 `<h3>` 标签生成右侧目录树。
   - 增加 **ScrollSpy** 滚动监听功能，实现阅读进度与右侧大纲高亮状态的实时同步联动，并支持点击大纲平滑滚动跳转。
3. **纯前端“毫秒级”全局搜索**
   - 替代了繁重的第三方搜索方案（如 Algolia）。
   - 在 `articles.html` 侧边栏新增搜索框，通过原生 JS 的 `filter` 方法监听输入事件。
   - 实现双维度实时检索：同时匹配文章标题和去除 HTML 标签后的纯文本正文。由于数据已预加载至内存，搜索体验达到真正的零延迟。

---

## 💡 未来优化方向预留

目前系统已满足日常写作与阅读需求，未来可考虑以下进阶特性：
1. **增强型代码块**：引入 `Prism.js` 实现语法高亮，并添加“一键复制”功能。
2. **轻量级可视化**：引入 `Mermaid.js` 支持在文章中直接书写图表语法。
3. **终极重构**：若文章体量与交互需求激增，考虑将纯原生架构迁移至现代 SSG（静态站点生成器，如 VitePress 或 Docusaurus），全面拥抱 Markdown/MDX 写作工作流。

---

## 💣 踩坑实录与解决方案

在项目的搭建与优化过程中，遇到了以下典型问题及解决方案，特此记录以备后查：

### 坑 1：本地预览跨域与资源路径报错
- **现象**：直接双击打开 `.html` 文件，页面排版错乱或者 API 请求失败。
- **原因**：本地通过 `file://` 协议打开网页，会触发浏览器的 CORS 安全限制，无法正常发起 fetch 请求读取 JSON。
- **解决**：使用 Node.js 工具启动本地 HTTP 服务，例如 `npx -y http-server -p 8085`，然后通过 `http://127.0.0.1:8085` 预览。

### 坑 2：GitHub 密钥泄露导致被强制撤回（Secret Scanning）
- **现象**：将 GitHub Token 硬编码写死在 `admin.html` 源码中进行 `git push` 时，终端报错 `GH013: Repository rule violations ... Push cannot contain secrets` 并拒绝推送。
- **原因**：GitHub 有非常严格的密钥扫描机制，检测到源码中包含明文 Token 会立即拦截以防止黑客盗用。
- **解决**：
  1. 将源码中的 Token 改为动态表单输入（存入 `localStorage`），确保代码中不包含敏感信息。
  2. 使用 `git reset --soft HEAD~1` 撤销包含了明文 Token 的错误提交。
  3. 重新提交并使用 `git push -f` 覆盖远程仓库历史。

### 坑 3：Git Push 连接超时 (443) 或 fetch first 冲突
- **现象**：终端频繁报 `fatal: unable to access ... Failed to connect to github.com port 443` 或 `[rejected] main -> main (fetch first)`。
- **原因**：国内直连 GitHub 不稳定；另外，本地历史记录与远程仓库有冲突。
- **解决**：配置 Git 全局 HTTP 代理（如 `git config --global http.proxy http://127.0.0.1:7897`）；确信本地代码是最新的前提下，使用 `-f` 参数强制推送。

### 坑 4：Twikoo 评论系统连接 MongoDB 失败
- **现象**：Vercel 部署成功，但前端发表评论失败。查看 Vercel Logs 显示 `MongoServerSelectionError` 和 `SSL alert number 80`。
- **原因 1**：连接字符串（`MONGODB_URI`）中密码包含了未转义的特殊字符（如 `@` 变成了 `@@`），导致解析失败。
- **原因 2**：MongoDB 开启了网络防火墙，默认只允许创建者的本地 IP 访问，拦截了 Vercel 服务器（动态 IP）的连接请求。
- **解决**：
  1. 检查并修正 Vercel 环境变量中的 MongoDB 连接字符串。
  2. 登录 MongoDB Atlas，在 Security -> Network Access 中添加 `0.0.0.0/0`（允许所有 IP 访问），等待生效后重启 Vercel 即可恢复正常。