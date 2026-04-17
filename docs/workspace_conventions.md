# 个人博客工作区：文件分类与命名规范

基于当前项目的混合架构（Astro + Vercel Serverless + 旧版静态后台）以及已有的 `CLAUDE.md` 约束，特制定以下工作区文件创建、命名与分类规范，确保项目持续迭代过程中的整洁与可维护性。

## 1. 目录架构与分类规则

文件存放必须严格遵循其功能作用域，**严禁在根目录或不相关的目录下堆放临时文件。**

| 目录层级 | 存放内容说明 | 存放规则与边界 |
| :--- | :--- | :--- |
| **根目录 `/`** | 项目级配置与规范文档 | 仅限全局配置（如 `package.json`, `astro.config.mjs`）和全局规范文档（如 `CLAUDE.md`, `readme.md`, `design_principles.md`）。绝不能放具体业务代码或测试文件。 |
| **`/src`** | Astro 前台源码 | 仅限前台页面的 UI 与逻辑。严禁将后台管理逻辑或一次性调试脚本混入。 |
| ├── `/src/pages` | 页面路由入口 | 这里的结构直接映射为网站的 URL 路由结构。新页面文件优先放这里。 |
| ├── `/src/components`| 可复用 UI 组件 | 跨页面复用的 UI 片段（如 Header, Footer, FloatingMenu）抽取到此处。 |
| ├── `/src/layouts` | 页面基础布局 | 承载页面的全局 HTML 骨架与插槽（如 `BaseLayout.astro`）。 |
| ├── `/src/styles` | 前台样式文件 | 存放全局 CSS 或复用的样式模块（如 `site.css`）。 |
| **`/api`** | Vercel Serverless 接口 | 后端业务逻辑。**一个文件对应一个明确的接口职责**。非接口逻辑不要放进这里。 |
| **`/public`** | 静态资源与旧版后台 | 可直接通过 URL 访问的静态文件。不要把源码组件塞进这里。 |
| ├── `/public/images` | 图片资源 | 存放博客文章插图、头像等（如 `my-avatar.jpg`, `img_*.png`）。 |
| ├── `/public/` (根) | 旧后台与基础脚本 | 存放 `admin.html`、基础 `script.js`、`style.css` 及 `favicon.svg` 等。 |

---

## 2. 文件命名规范

为保持代码库的统一性，不同类型的文件采用不同的命名风格：

### 2.1 Astro 组件与布局 (PascalCase)
- **规则**：大驼峰命名法，首字母大写。
- **适用范围**：`/src/components/` 和 `/src/layouts/`。
- **示例**：`FloatingMenu.astro`、`BaseLayout.astro`。

### 2.2 页面路由与静态资源 (lowercase / kebab-case)
- **规则**：全小写，单词间用连字符 `-` 连接。因为这些文件名通常直接暴露在 URL 中。
- **适用范围**：`/src/pages/`、`/public/`（包含图片）。
- **示例**：`index.astro`、`articles.html.astro`、`admin.html`、`friend-avatar.jpg`。
- *注：通过工具自动上传生成的图片，保留原时间戳格式即可（如 `img_1774010498471.png`）。*

### 2.3 后端接口文件 (camelCase)
- **规则**：小驼峰命名法，以动词开头，清晰表达接口意图。
- **适用范围**：`/api/` 目录下的 Serverless 函数。
- **示例**：`deleteArticle.js`、`fetchLinkTitle.js`、`saveArticle.js`。
- **特殊约定**：内部共享的数据库连接或工具模块，使用下划线前缀以区分对外接口，如 `_db.js`。

### 2.4 文档与配置文件
- **规则**：遵循业界常规（通常为全小写）。
- **示例**：`package.json`、`readme.md`、`spec.md`。
- **特殊约定**：最高约束文档保持全大写 `CLAUDE.md` 以示强调。

---

## 3. 文件创建决策指南（当你需要加东西时）

**场景 1：我要加一个前台展示的新网页（如“友链页”）**
👉 **动作**：在 `/src/pages/` 下创建 `friends.astro`。

**场景 2：我要把文章列表的卡片单独抽出来复用**
👉 **动作**：在 `/src/components/` 下创建 `ArticleCard.astro`。

**场景 3：我要给后台 `admin.html` 增加一个“获取网站摘要”的后端功能**
👉 **动作**：在 `/api/` 下创建 `getSiteSummary.js`，并使用驼峰命名。

**场景 4：我要上传一张说明图，并在文章中引用**
👉 **动作**：将图片放入 `/public/images/`，命名为 `xxx-architecture.png`，确保名字有语义，或直接使用上传工具生成的 `img_*.png`。

**场景 5：我要记录一个 Vercel 部署相关的深坑经验**
👉 **动作**：不要新建文档，直接修改根目录的 `readme.md`，并在需要时让我更新 `memory.md`。
