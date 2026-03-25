# 个人博客项目演进与技术架构记录

本文档用于记录当前个人博客从初始创建到后续优化的完整演进过程，以及项目所采用的核心技术栈与架构设计。

---

## 🏗️ 核心技术栈与架构概览

本博客从初期的**纯无后端（Serverless）静态架构**演进为了现在的**全栈 Serverless 架构**，彻底解决了数据拉取限流问题，并为未来扩展打下了坚实的基础。

### 1. 技术选型
- **前端核心**：纯原生 HTML5, CSS3 (CSS Variables), Vanilla JavaScript (原生 JS)
- **数据交互**：Fetch API
- **部署与托管**：GitHub Pages (前端静态站点), Vercel (后端 API 接口)
- **内容存储**：MongoDB Atlas (文章与评论数据库), GitHub 仓库 (仅用作图片床)
- **评论系统**：Twikoo (基于 Vercel 部署服务，数据同存 MongoDB Atlas)
- **域名解析**：腾讯云自定义域名绑定 (前端绑定 GitHub Pages，后端 API 绑定 Vercel 子域名解决 DNS 污染)

### 2. 系统架构设计
- **前端页面展示**：用户访问 GitHub Pages 托管的静态页面。
- **文章数据流转 (Vercel API)**：
  - **前台读取**：通过 JS 动态调用部署在 Vercel 的自定义 API (`api.aoiblog.top`) 从 MongoDB 实时读取文章数据渲染。
  - **后台管理**：通过 `admin.html` 页面输入 Vercel Admin Token 进行鉴权，通过 Vercel API 对 MongoDB 进行文章的增删改查。
  - **静态资源**：图片上传依然通过 GitHub API 直接推送到仓库的 `images/` 目录，兼顾免费图床。
- **评论数据流转**：前台页面嵌入 Twikoo 脚本，将评论数据读写至部署在 Vercel 上的 Twikoo 接口，最终落盘到 MongoDB Atlas 云数据库。

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
6. **后台评论管理**：在 `admin.html` 中新增“最新评论”面板，通过直接调用 Twikoo API (`POST /event: GET_RECENT_COMMENTS`)，实现了在博客后台集中查看、按时间倒序排序全站评论。系统能智能区分**“主页留言板”**与**“文章评论”**并打上标签，支持一键跳转至对应页面进行回复或删除操作。

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
4. **首页重构与交互提升**
   - **Hero 区域增强**：修改了首页首屏的文案，并引入了基于 JavaScript 的纯手写**“打字机 (Typewriter) 动画特效”**和光标闪烁效果，增加了“阅读最新文章”等引导按钮。
   - **知识专栏导航**：在首页新增了“知识专栏”网格卡片（如前端开发、算法刷题等）。
   - **文章分类过滤**：在 `articles.html` 中增加了对 URL 参数（`?category=xxx`）的解析逻辑，使得从首页点击分类卡片可以直接跳转并自动过滤显示对应分类的文章。
   - **全局留言板**：将首页原有的静态联系表单重构为基于 Twikoo 的全局留言板，路径设为 `/`，与文章评论系统数据互通。
5. **全局悬浮交互菜单 (Floating Menu)**
   - 在页面右下角增加了一个类似于“交互式看板娘”的悬浮按钮 🤖。
   - 点击展开后提供多个快捷操作：**返回顶部**、**随机阅读**（在文章库中随机抽取一篇文章并平滑跳转）、**切换主题**。
   - 该组件纯 HTML/CSS/JS 实现，带有平滑的弹出动画与图标状态同步。
6. **移动端响应式优化**
   - 取消移动端导航栏的固定定位，避免高度过大遮挡页面顶部内容。
   - 缩小导航菜单项的间距与字号，开启折行，提升小屏幕下的排版紧凑感。
7. **文章阅读历史追踪与进度监控**
   - 实现了基于 `localStorage` 的本地阅读状态记录功能，类似主流算法笔记网站。
   - **优化逻辑**：引入了滚动事件监听，不再是点击即“已读”。只有当访客真正滚动阅读至文章内容的 **90% 以上** 时，系统才会判定为“已读”，并在左侧列表打上绿色的 `✔️已读` 标签。
   - **视觉反馈**：在文章标题下方新增了**动态阅读进度条**和**百分比提示**，实时反馈当前阅读位置，极大提升了长文的阅读体验。

### 阶段三：后端架构演进与全栈重构 (Vercel Serverless + MongoDB)
在阶段一和阶段二中，博客完全依赖前端直接调用 GitHub API 读取 `articles.json` 作为数据源。然而，随着开发调试的频繁进行，暴露出一个致命缺陷：**GitHub API 对未授权的 IP 有极其严格的每小时 60 次的 Rate Limit 限流**。为了彻底摆脱这个限制，并为未来引入真实的“全局完整阅读量”等需要后端计算的功能做准备，项目进行了后端分离重构。

**重构步骤与架构演进：**
1. **API 开发与部署 (Serverless)**：
   - 放弃了纯静态 JSON 方案，在项目内新增 `api/` 目录。
   - 使用 Node.js 编写了 `getArticles.js`, `saveArticle.js`, `deleteArticle.js` 等符合 Vercel Serverless 规范的接口。
   - 配置 `vercel.json` 路由，将后端接口成功部署至 Vercel 平台。
2. **数据库接入 (MongoDB Atlas)**：
   - 使用免费的 MongoDB Atlas 云数据库建立真实的云端集合 `my_blog_db.articles`。
   - 在 Serverless 函数中通过 `mongodb` 驱动建立连接池，实现真实的数据读写。
3. **域名与 DNS 优化 (绕过国内污染)**：
   - **痛点**：Vercel 默认提供的 `.vercel.app` 域名在国内长期遭受 DNS 污染，导致 API 请求超时 (`ConnectTimeoutError`)，甚至解析到 Facebook 的黑洞 IP。
   - **解决**：利用腾讯云申请的未备案主域名 (`aoiblog.top`)，在 Vercel 中为其分配了自定义子域名 `api.aoiblog.top`。
   - 在腾讯云 DNSPod 中配置 `CNAME` 指向 `cname.vercel-dns.com`，从而完美实现了**国内免翻墙秒开接口**。
4. **前端改造与平滑数据迁移**：
   - 将 `index.html`、`articles.html` 以及 `admin.html` 中所有的 `api.github.com` 数据请求路径全部替换为自己的 `https://api.aoiblog.top/api/...`。
   - 编写了 Node.js 脚本 `migrate.js`，通过运行 `node migrate.js <ADMIN_TOKEN>`，将旧版 `articles.json` 中的历史文章一键批量导入 MongoDB。
5. **重构成果**：
   - 目前文章的获取、发布、删除均已完全脱离对 GitHub `contents` API 的依赖。
   - 后台管理页面仅保留了 GitHub 用于免费图片上传的图床功能。
   - 真正实现了前后端分离的现代 Web 架构，国内访问流畅且永不限流。

5. **新增代码块高亮与 Mac 风格 UI (Prism.js)**：
   - 在 `articles.html` 引入 Prism.js 及其插件（行号、语言显示、一键复制）。
   - 将 Prism.js 的主题切换为 `prism-vsc-dark-plus`，实现与 VSCode 极其相似的代码高亮配色。
   - 在 `style.css` 中自定义 `.mac-style-code` 类，纯手写 Mac 风格“红黄绿”三个小圆点装饰。
   - 在 `admin.html` 编辑器中新增“插入代码块”快捷按钮。
6. **后台编辑器增强 HTML 快捷插入功能**：
   - 在 `admin.html` 编辑器中新增“插入跳转链接”按钮，支持选中文字后一键生成带有 `target="_blank"` 属性的 `<a>` 标签。
   - 新增“加粗 (B)”、“小标题 (H3)”、“红字”、“蓝字”、“黄字”快捷按钮，方便通过纯 HTML 语法直接在后台进行富文本排版。
7. **动态分类 (知识专栏) 架构升级**：
   - 彻底移除了 `index.html` 和 `articles.html` 中硬编码的分类写死逻辑。
   - 前端通过拉取文章数据自动提取唯一分类，并在页面上动态生成分类卡片和筛选按钮。
   - `admin.html` 中加入了“添加新栏目”功能，支持用户在发布/修改文章时随时创建自定义分类，且无需修改后端或数据库 schema 即可自动持久化展示。

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

### 坑 5：挂代理（翻墙）后评论区消失
- **现象**：在正常网络下可以正常查看和发布评论，但开启代理软件（如全局模式）后，评论区组件无法加载并消失。
- **原因**：为了让国内访客获得最快的加载速度，项目在 `articles.html` 等页面中引入 Twikoo 核心脚本时，使用了专为国内优化的 CDN（如七牛云 `cdn.staticfile.net`）。部分国内 CDN 会直接拒绝来自海外 IP（代理节点）的请求，或者代理软件的广告拦截规则（AdBlock）将评论请求误认为追踪器进行拦截。
- **解决**：
  1. **方案一（推荐，无需改代码）**：将代理软件从“全局模式”切换为“规则模式（Rule）”或“绕过大陆/直连模式”，让访问博客时不经过代理，确保国内访客的极致体验不受影响。
  2. **方案二（折中）**：如果必须要求在全局代理下也能访问，可将代码中的 CDN 链接替换为全球通用的 CDN（如 `unpkg` 或 `cloudflare`），代价是国内部分地区的加载速度可能会有所下降。本项目目前选择保持现状，优先保障国内访问体验。

### 坑 6：Vercel Serverless API 国内连通性问题 (DNS 污染)
- **现象**：使用 `xxx.vercel.app` 域名进行 API 请求时，在终端或国内网络环境下高概率出现 `ConnectTimeoutError` 或被重定向到 Facebook 的 IP (`31.13.70.9`)。
- **原因**：Vercel 免费分配的 `.vercel.app` 二级域名在国内长期遭受 DNS 污染，导致解析到错误的黑洞 IP。
- **解决**：在 Vercel 后台中为项目绑定**自定义子域名**（如 `api.aoiblog.top`），并在国内的 DNS 服务商（如腾讯云 DNSPod）中将该子域名 `CNAME` 解析到 `cname.vercel-dns.com`。由于你自己的主域名没有被污染，通过这种方式可以完美实现国内免翻墙高速直连 API。

### 坑 7：Vercel Serverless 路由 404 问题
- **现象**：访问 `/api/saveArticle` 时，Vercel 返回 `The page could not be found` 的 HTML 页面，而不是执行对应的 Node.js 函数。
- **原因**：`vercel.json` 路由配置不当。旧版配置 `"dest": "/api/$1"` 可能会被 Vercel 当作静态目录查找，而不是匹配到 `saveArticle.js` 这个可执行文件。
- **解决**：在 `vercel.json` 的 routes 中显式加上 `.js` 后缀，如：`"src": "/api/(.*)", "dest": "/api/$1.js"`，确保请求精确路由到函数文件。

### 坑 8：CORS 预检请求拦截导致 "Failed to fetch" (跨域请求头缺失)
- **现象**：在后台页面发布文章时，前端报错 `同步到云端失败: Failed to fetch`。
- **原因**：前端发送带有 `Authorization: Bearer <token>` 的跨域 POST 请求时，浏览器会先发送 `OPTIONS` 预检请求。如果后端接口的响应头 `Access-Control-Allow-Headers` 中没有包含 `Authorization`，浏览器会认为服务器拒绝携带该鉴权信息，直接拦截真实的 POST 请求。
- **解决**：在后端的 API 文件（如 `saveArticle.js`、`deleteArticle.js`）中，修改跨域响应头设置，显式添加 `Authorization` 支持：
  `res.setHeader('Access-Control-Allow-Headers', '..., X-Api-Version, Authorization');`

### 坑 9：动态添加 Select 选项导致表单验证拦截（发布失败）
- **现象**：在后台管理页面 (`admin.html`) 中点击“添加新栏目”，输入新栏目名称并写完文章后，点击“保存文章到云端数据库”毫无反应，或者浏览器弹出“请选择列表中的一项”的系统提示。
- **原因**：前端通过 JavaScript 动态向 `<select required>` 元素中追加了一个 `<option>`，并尝试使用 `select.value = "新栏目"` 的方式选中它。但在部分浏览器中，由于 DOM 渲染的微小延迟，这种赋值方式并未能成功改变 `<select>` 内部的选中状态，导致其值仍然为空 (`""`)。因此触发了 HTML5 的原生表单验证，阻止了文章的提交。
- **解决**：修改 JavaScript 赋值逻辑，放弃直接修改 `value` 的不可靠做法。在动态追加 `<option>` 后，通过直接修改 `selectedIndex` 属性（例如 `select.selectedIndex = select.options.length - 1;`）强制浏览器在底层状态树中指向刚刚添加的新选项，从而完美绕过表单的 `required` 拦截。

### 坑 10：保存文章时提示请求失败 401 (Unauthorized)
- **现象**：在后台发布或删除文章时，弹出错误提示 `同步到云端失败: 请求失败: 401`。
- **原因**：`401` 状态码代表“未授权”，说明前端通过 `localStorage` 携带发送的 `ADMIN_TOKEN`，与部署在 Vercel 上的环境变量 `ADMIN_TOKEN` 的值不匹配。这通常是因为前端填错了密码，或者是 Vercel 上修改了环境变量后**没有重新部署 (Redeploy)** 导致新密码未生效。
- **解决**：
  1. 登录 Vercel 后台，进入项目的 **Settings -> Environment Variables**，核对 `ADMIN_TOKEN` 的值。
  2. 如果修改了该值，必须前往 **Deployments** 页面点击右上角的 **Redeploy**，新环境变量才能在 Serverless 函数中生效。
  3. 在博客后台管理页面点击右上角的“重新配置”，填入与 Vercel 上完全一致的 `ADMIN_TOKEN`。

### 坑 11：数据加载失败，提示 CORS 跨域拦截 (Access-Control-Allow-Origin)
- **现象**：访问博客前台时，文章列表一直显示“加载中...”。按 F12 打开控制台，发现红色报错：`has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present on the requested resource`。
- **原因**：虽然我们在 Vercel 的 Serverless API（如 `getArticles.js`）代码里通过 `res.setHeader('Access-Control-Allow-Origin', '*');` 写死了允许跨域，但这只对**成功执行的代码**有效。如果 API 在执行到 `setHeader` 之前就崩溃了（例如 MongoDB 连接失败、代码语法错误等），Vercel 引擎会直接接管并返回一个 500 错误页面。而 Vercel 默认的 500 错误页面是**不带任何 CORS 头**的！因此，浏览器收到这个 500 响应时，因为没看到 CORS 头，就会报出误导性的“跨域拦截”错误，掩盖了真实的 500 报错。
- **解决**：
  1. 遇到 CORS 报错时，不要只查前端代码。立刻登录 Vercel 控制台，进入对应的后端项目。
  2. 切换到 **Logs**（日志）面板，筛选 `Error`。
  3. 查看真实的报错原因（通常是 `MongoServerSelectionError` 数据库连不上，或者是改坏了后端的代码）。修复真实的后端 Bug 后，CORS 报错会自动消失。

### 坑 12：Vercel 边缘缓存拦截导致 OPTIONS 预检请求失败 (403 Forbidden / CORS 错误)
- **现象**：在解决缓存问题时，为了防止浏览器缓存文章列表，在 `fetch` 请求的 URL 后强行拼接了时间戳 `?t=12345`，或者添加了自定义请求头 `headers: { 'Accept': 'application/json' }`。结果前台和后台全部崩溃，控制台报错 `403 (Forbidden)` 或依然提示 CORS 跨域错误，且 Vercel 的 Logs 里**完全没有这些错误请求的日志**。
- **原因**：
  1. **自定义 Header 触发预检**：在跨域 (CORS) 请求中，只要添加了 `Accept` 等非简单请求的 Header，浏览器就会自动发送一个隐藏的 `OPTIONS` 预检请求。
  2. **Vercel 边缘节点拦截**：Vercel 的免费版边缘网络 (Edge Network) 和防火墙机制，对未在配置中明确声明允许的 `OPTIONS` 请求或带有可疑动态参数（如随机时间戳 `?t=`）的路由，可能会直接在边缘层进行拦截并返回 403 或不带跨域头的 500/502 错误。由于请求被边缘节点直接丢弃，所以 Serverless 函数根本没有被执行，Vercel Logs 里也就没有记录。
- **解决**：
  1. 放弃在 URL 上手动拼接时间戳破坏缓存的“土办法”。
  2. 去除 `fetch` 中任何不必要的自定义 `headers`，确保其降级为“简单请求”，避免触发 `OPTIONS` 预检。
  3. 使用原生且最标准的 Fetch API 参数 `cache: 'no-store'` 来告诉浏览器和 CDN 不要缓存数据。
  **正确代码示例**：
  ```javascript
  const response = await fetch('https://api.aoiblog.top/api/getArticles', {
      method: 'GET',
      cache: 'no-store' // 完美替代时间戳，且不触发 OPTIONS 拦截
  });
  ```

### 坑 13：浏览器顽固缓存导致 HTML 代码更新不生效 (假性持续报错)
- **现象**：代码已经推送到 GitHub Pages 并成功部署，甚至通过脚本验证线上已经是最新代码，但浏览器里按 `Ctrl + F5` 强制刷新后，F12 控制台里的报错依旧，且请求 URL 里依然带有旧版本的代码特征（如已经被删掉的 `?t=时间戳`）。
- **原因**：某些现代浏览器（如 Chrome, Edge）对 HTML 文件内联的 JavaScript 脚本缓存极其顽固。普通的刷新甚至 `Ctrl + F5` 有时无法彻底清除这层状态缓存，导致浏览器依然使用带有错误逻辑（如触发 403 惩罚）的旧代码发送请求。
- **解决**：
  1. 按 `F12` 保持开发者工具处于打开状态。
  2. 鼠标**右键长按**浏览器地址栏左侧的“刷新 🔄”按钮。
  3. 在弹出的菜单中选择 **“清空缓存并硬性重新加载” (Empty Cache and Hard Reload)**。
  4. 或使用无痕/隐私模式 (`Ctrl + Shift + N`) 进行测试验证。