# 个人博客项目说明

这个仓库是我的个人博客项目，当前采用“`Astro 前台 + Vercel Serverless API + MongoDB + 保留旧版 admin 后台`”的架构。

这份文档的目标有两个：

1. 记录项目当前可运行的真实架构
2. 持续记录重要改动过程、踩坑和维护约定

后续只要继续在这个仓库里做改动，都应同步更新本文件中的“变更记录”和“踩坑记录”，不再依赖额外提醒。

---

## 当前架构

### 前台
- 前台框架：Astro
- 风格方向：AstroPaper 风格阅读型博客
- 主页入口：`src/pages/index.astro`
- 文章页入口：`src/pages/articles.html.astro`
- 全局布局：`src/layouts/BaseLayout.astro`
- 公共组件：`src/components/`
- 全局样式：`src/styles/site.css`

### 后台与数据
- 后台页面：`public/admin.html`
- 前台公共脚本：`public/script.js`
- 旧版样式文件：`public/style.css`
- 文章接口：`api/getArticles.js`
- 保存接口：`api/saveArticle.js`
- 删除接口：`api/deleteArticle.js`
- 数据库：MongoDB
- 评论系统：Twikoo

### 部署
- 前台构建：Astro static build
- 后端接口：Vercel Serverless Functions
- 当前远端仓库：`origin -> https://github.com/langhuanaibu/my-blog.git`
- 当前主分支：`main`

---

## 目录说明

```text
api/                    Vercel Serverless API
public/                 静态资源、旧后台、旧脚本
src/components/         前台公共组件
src/layouts/            Astro 布局
src/pages/              Astro 页面入口
src/styles/             Astro 前台样式
.nvmrc                  当前项目 Node 版本
astro.config.mjs        Astro 配置
package.json            依赖与脚本
vercel.json             Vercel 路由配置
```

---

## 本次改造说明

这次改造的目标是：

- 使用 Astro 重做博客前台
- 保留现有 Vercel API
- 保留 MongoDB 数据结构
- 保留 `admin.html` 后台
- 不改首页核心文字内容
- 不改已有博客文章内容

### 本次完成的内容

1. 将前台重构为 Astro 页面结构
2. 将整体视觉改造成 AstroPaper 风格的阅读型博客
3. 新增统一布局、导航、页脚、悬浮菜单和全局样式
4. 首页保留原有核心文案，只调整布局和视觉表现
5. 文章页改为更适合阅读的三栏结构
6. 保留文章接口读取逻辑、Twikoo 评论逻辑和本地阅读进度逻辑
7. 保留旧后台 `public/admin.html` 不动
8. 增加 favicon
9. 增加 Node 版本约束和 `.nvmrc`
10. 补充 `.gitignore`，忽略 Astro 与构建产物

### 本次改造涉及文件

- `src/pages/index.astro`
- `src/pages/articles.html.astro`
- `src/layouts/BaseLayout.astro`
- `src/components/Header.astro`
- `src/components/Footer.astro`
- `src/components/FloatingMenu.astro`
- `src/styles/site.css`
- `public/script.js`
- `public/favicon.svg`
- `.nvmrc`
- `.gitignore`
- `package.json`

### 本次没有改动的内容

- 首页核心文案
- 已有博客文章正文
- MongoDB 数据结构
- `api/` 目录的业务接口
- `public/admin.html` 后台管理逻辑

---

## 当前 Node 版本约定

这个项目现在要求使用较新的 Node 版本，因为当前 Astro 版本不再支持 Node 16。

### 当前项目固定版本

- `.nvmrc`: `24.14.1`

### 使用方式

进入本项目后执行：

```powershell
nvm use 24.14.1
```

如果另一个旧项目仍然使用 Node 16，则进入那个项目后执行：

```powershell
nvm use 16.20.2
```

### 当前 package.json 中的约束

项目已写入：

```json
"engines": {
  "node": ">=24.14.1"
}
```

---

## 常用命令

安装依赖：

```powershell
npm install
```

开发模式：

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

---

## 路由约定

### 当前前台路由

- 首页：`/`
- 文章页：`/articles.html`

### 说明

文章页文件名使用 `articles.html.astro`，是为了尽量兼容旧链接和旧跳转逻辑。这样原来很多指向 `articles.html` 的链接不需要额外改动。

---

## 变更记录

### 2026-04-06

#### AstroPaper 风格前台改造
- 完成 Astro 前台重构
- 前台样式切换为 AstroPaper 风格
- 首页改造成阅读型布局
- 文章页改造成三栏阅读布局
- 保留首页核心文字和文章内容
- 保留后台和 API 架构不动

#### Node 版本治理
- 检查并确认本机已安装 `nvm-windows`
- 安装 Node `24.14.1`
- 将当前项目切换到 Node `24.14.1`
- 新增 `.nvmrc`
- 更新 `package.json` 中的 `engines.node`

#### 验证结果
- `npm run build` 构建成功
- 本地预览 `/` 返回 `200`
- 本地预览 `/articles.html` 返回 `200`
- 改造已提交并推送到 `main`

#### Vercel 部署兼容修复
- 将 `package.json` 中的 Node 版本约束从 `>=24.14.1` 调整为 `24.x`
- 删除 `vercel.json`
- 原因是当前项目已经是标准 Astro 静态站结构，Vercel 对 Astro 项目通常使用零配置更稳
- 顶层 `api/` 目录本身就是 Vercel Functions 约定路径，不需要再额外写 `/api/(.*) -> /api/$1.js` 的 rewrite

---

## 踩坑记录

### 1. Astro 不支持 Node 16

#### 现象
执行 `npm run build` 时失败，提示：

```text
Node.js v16.20.2 is not supported by Astro
Please upgrade Node.js to a supported version: ">=22.12.0"
```

#### 原因
当前安装的 Astro 版本已经不支持 Node 16。

#### 解决
- 使用 `nvm-windows`
- 安装并切换到 `Node 24.14.1`
- 给项目增加 `.nvmrc`

---

### 2. Windows 下大补丁容易触发命令长度限制

#### 现象
一次性用大 patch 重写多个文件时失败，报错类似：

```text
CreateProcessAsUserW failed: 206
```

#### 原因
Windows 对命令长度有限制，大体积补丁容易超限。

#### 解决
- 将补丁拆成多个小 patch 分次提交
- 优先按文件拆分修改

---

### 3. 终端中文乱码不一定代表文件内容损坏

#### 现象
PowerShell 输出 Astro 文件时，中文显示成乱码。

#### 原因
通常是终端输出编码和文件编码不一致，不一定是源码本身损坏。

#### 解决
- 用 `findstr /n`、`Get-Content -Encoding UTF8` 等方式交叉确认
- 重点检查引号、数组、模板字符串等关键语法位置

---

### 4. 构建产物和 Astro 缓存不应该进入版本库

#### 现象
构建后 `git status` 出现 `.astro/`、`dist/`、`node_modules/.vite/` 等变化。

#### 原因
缺少针对 Astro 项目的忽略规则。

#### 解决
已在 `.gitignore` 中补充：

```gitignore
node_modules/
.astro/
dist/
```

---

### 5. Astro 项目在 Vercel 上尽量不要额外写 rewrite

#### 现象
项目本地 `npm run build` 正常，但 Vercel 端可能出现部署异常、路由行为不一致，或者部署后访问结果和本地预览不完全一致。

#### 原因
当前项目已经是标准 Astro 静态站，同时仓库根目录还有顶层 `api/` 目录。对这种结构来说：

- Astro 前台通常用 Vercel 零配置部署更稳
- 顶层 `api/*.js` 本身就是 Vercel Functions 的默认约定路径
- 额外再写 `vercel.json` 的 rewrite，反而容易让 Astro 路由和 Vercel 路由叠加，增加不确定性

#### 解决
- 删除 `vercel.json`
- 保留 Astro 默认构建输出
- 保留顶层 `api/` 目录作为 Vercel Functions

---

### 6. Node 版本约束在部署平台上不要写得过窄

#### 现象
本地能用某个精确 Node 版本运行，但部署平台对精确 patch 版本的识别不一定完全一致。

#### 原因
像 `>=24.14.1` 这种写法虽然本地可用，但在部署平台上不如 `24.x` 这种主版本范围更稳、更符合托管平台的识别习惯。

#### 解决
在 `package.json` 中优先写：

```json
"engines": {
  "node": "24.x"
}
```

本地仍然继续通过 `.nvmrc` 固定具体版本：

```text
24.14.1
```

---

### 7. `node_modules` 即使写进了 `.gitignore`，如果之前已经提交过，Vercel 仍然会拉到仓库里

#### 现象
Vercel 部署时出现：

```text
Command "npm run build" exited with 126
```

本地构建正常，但线上构建在安装依赖后直接失败。

#### 原因
`.gitignore` 只能阻止“新文件继续被追踪”，不能自动把“之前已经提交进 Git 的 `node_modules/`”移出版本库。

如果仓库里已经追踪了从 Windows 提交上去的 `node_modules/.bin/*` 文件，Vercel 的 Linux 构建环境就可能因为可执行权限或脚本兼容问题触发 `exit 126`。

#### 解决
确认 `node_modules/` 已写入 `.gitignore` 后，还必须执行一次：

```powershell
git rm -r --cached node_modules
git commit -m "fix: remove tracked node_modules from repo"
git push origin main
```

这样只会把 `node_modules` 从 Git 跟踪中移除，不会删除本地磁盘里的依赖目录。

---

### 8. Vercel 项目框架预设选错会把 Astro 项目当成 Next.js

#### 现象
Vercel 部署页面出现类似报错：

```text
No Next.js version detected. Make sure your package.json has "next" in either "dependencies" or "devDependencies".
```

#### 原因
这不是仓库里真的缺少 `next`，而是 Vercel 项目设置里的 **Framework Preset** 被错误设成了 `Next.js`。

当前项目实际是：

- 前台：Astro
- 后端：顶层 `api/` 目录中的 Vercel Functions

所以一旦项目预设成 Next.js，Vercel 就会按 Next.js 的构建逻辑去检查并报错。

#### 解决
到 Vercel 项目设置中手动改为正确的构建方式：

- Framework Preset：`Astro`
- Root Directory：仓库根目录
- Build Command：`npm run build`
- Output Directory：`dist`

如果这个项目是之前用错误预设创建出来的，也可以直接重新导入仓库并选择 Astro。

---

### 9. GitHub Pages 误用 Jekyll 导致 Astro 构建报错

#### 现象
在 GitHub 的 Actions 页面，自动触发的 `pages build and deployment` 任务持续失败，并在 `build` 阶段报错：
```text
Logging at level: debug GitHub Pages: github-pages v232 GitHub Pages: jekyll v3.10.0 Theme: jekyll-theme-primer ... Requiring:
```

#### 原因
项目实际部署在 Vercel 上，但 GitHub 仓库默认开启了 GitHub Pages，且没有配置专门的 Astro 构建工作流。因此，GitHub Pages 默认使用自带的 Jekyll（基于 Ruby）来尝试构建我们的 Node.js/Astro 项目。Jekyll 无法理解 Astro 的项目结构（如 `.astro` 或 `node_modules` 等带有特殊符号的文件），从而导致构建崩溃。

#### 解决
- **方案一（推荐）**：在项目根目录创建一个名为 `.nojekyll` 的空文件。这会明确告诉 GitHub 不要使用 Jekyll 来构建此仓库，从而消除由于 Jekyll 解析导致的报错。
- **方案二**：直接前往 GitHub 仓库的 `Settings -> Pages`，将 `Build and deployment` 的 Source 设置为 `None`，彻底关闭 GitHub Pages 功能。

---

## 维护约定

后续在这个仓库继续改动时，默认遵守以下约定：

1. 只要有重要结构调整，就更新本 README 的“当前架构”
2. 只要有值得记录的修改，就更新“变更记录”
3. 只要踩到新坑，就更新“踩坑记录”
4. 如果改动影响运行方式、Node 版本、部署方式，也必须写进 README
5. 如果改动影响首页文案、文章内容、后台逻辑或 API 结构，需要明确标注

---

## 后续可继续优化的方向

- 首页增加更精细的文章卡片排版
- 文章页加入上一篇/下一篇导航
- 为文章页补充 SEO 元信息生成
- 将部分首页数据获取逻辑进一步组件化
- 后续视需要决定是否把内容管理迁移到更完整的 Astro 内容体系
---

## 2026-04-06 补充记录

### API 同域回切修复
- 将前台页面和 `public/admin.html` 中写死的 `https://api.aoiblog.top/api/*` 改为同域 `/api/*`
- 本次改动不涉及文章正文、MongoDB 结构或后台表单逻辑

### 首页 Hero 与导航微调
- 顶部导航移除“博客”和“后台”入口
- 首页 Hero 右侧改为展示旧版首页头图 `/images/img_1774022028502.png`
- 移除“写作自述”卡片，保留首页主标题、原文案和两个主按钮

### 头像与友链更新
- 新增 `public/images/friend-avatar.jpg` 作为朋友友链头像
- 新增 `public/images/my-avatar.jpg` 作为博客导航头像和我的友链头像
- 朋友友链文案改为“漫漫长路，原作清风伴君途”

### 后台发文链路检查
- 后台页面当前通过同域 `/api/saveArticle`、`/api/getArticles`、`/api/deleteArticle` 与 Vercel Functions 通信
- 发文成功后会立即重新拉取文章列表，前台首页与文章页也都从同域 `/api/getArticles` 读取数据
- 本地仓库未提供 `.env`，因此无法在本机完整模拟 MongoDB 与管理员口令环境；线上是否能真正发布成功取决于 Vercel 项目里是否已配置 `MONGODB_URI` 和 `ADMIN_TOKEN`

### 后台插入网址标题链接
- 后台编辑器新增“插入网址链接”按钮
- 输入外部网址后，后台会通过同域接口 `/api/fetchLinkTitle` 抓取目标网页标题
- 插入到文章正文中的结果为可点击 `<a>` 链接，前台阅读界面直接显示网页原标题并可跳转
- 如果目标网页标题抓取失败，会自动回退为“以网址原文作为链接文字”插入，避免发文中断

### GitHub Pages 失败邮件说明
- 当前主站已经迁移到 Vercel，但 GitHub 仓库侧如果还开启了 Pages，GitHub 仍会尝试对仓库做默认 Pages 构建
- 本仓库根目录没有站点专用的 `.github/workflows` Pages 工作流，若 Actions 里出现 `pages build and deployment`，通常是 GitHub Pages 设置仍然开启，且正在走默认 Jekyll 构建
- 这类失败邮件一般不影响 Vercel 线上站点访问
- 如果后续完全不再使用 GitHub Pages，建议到 GitHub 仓库 `Settings -> Pages` 里关闭 Pages 部署，避免持续收到失败邮件

### 新踩坑
#### `api.aoiblog.top` 可能被 Vercel Security Checkpoint 单独拦截
- 现象：文章列表和后台请求接口失败，接口直接返回 `403 Vercel Security Checkpoint`
- 原因：页面从 `www.aoiblog.top` 跨域请求 `api.aoiblog.top` 时，Vercel 可能把 `api` 子域名当成独立站点再次做浏览器校验
- 解决：优先统一使用当前站点同域接口

```text
/api/getArticles
/api/saveArticle
/api/deleteArticle
```

---

### 10. 使用 Pretext 优化前端文本测量与布局

#### 现象
在博客首页截断摘要（直接切 100 字符）会导致半个单词被截断、卡片高度不一；在文章列表页，若一次性渲染所有文章的 DOM 节点，长列表会导致页面滚动卡顿。

#### 原因
传统的前端文本截断和高度测量通常依赖于将元素插入 DOM 后读取 `offsetHeight`，这种做法会触发浏览器昂贵的重排（Reflow），在长列表或瀑布流布局中会导致严重的性能问题（Layout Thrashing）。

#### 解决
引入了 `@chenglou/pretext` 库，这是一个极速、不依赖 DOM 的文本测量与布局引擎。
- **使用 ES Module 引入**：在 Astro 的 `<script is:inline>` 中使用 pretext 时，需要改为 `<script type="module" is:inline>` 以便支持 `import` 语法。
- **精准多行截断**：在首页摘要中，使用 `prepareWithSegments` 和 `layoutWithLines` 提前计算出正好适应容器宽度的 3 行文本，拼接后插入 DOM，取代了不可控的 CSS `-webkit-line-clamp`。
- **长列表虚拟化**：在文章列表页，使用 pretext 极速预计算每篇文章标题由于换行导致的精确高度。结合固定边距得出每个列表项的绝对高度和偏移量（top）。然后在 `scroll` 事件中，仅渲染可视区域内的文章节点，并使用绝对定位。这样无论文章多少，DOM 节点数始终保持在极低水平，实现了高性能的虚拟列表。
- **瀑布流布局**：最初尝试使用 pretext 预计算首页分类卡片的高度并进行绝对定位，但由于卡片中包含了 emoji 图标、不同级别的标题以及边距，这些元素在不同操作系统和浏览器下的实际渲染高度（包括行高差异）难以做到 100% 精确的像素级预估，导致最终渲染时卡片出现了由于绝对定位计算不准带来的高度溢出或重叠。为了保证完美的视觉效果，现已**改用原生的 CSS Multi-column（多列布局）**。CSS Multi-column 同样不需要 JS 频繁操作 DOM 和测量，性能极佳，且由浏览器引擎负责排版，彻底避免了跨端兼容和字体渲染差异带来的错位问题。
