# 个人博客工作区：文件分类与命名规范

基于当前项目架构（Hexo + Fluid + Vercel）以及已有的 `CLAUDE.md` / `AGENTS.md` 约束，特制定以下工作区文件创建、命名与分类规范，确保项目持续迭代过程中的整洁与可维护性。

## 1. 目录架构与分类规则

文件存放必须严格遵循其功能作用域，**严禁在根目录或不相关的目录下堆放临时文件。**

| 目录层级 | 存放内容说明 | 存放规则与边界 |
| :--- | :--- | :--- |
| **根目录 `/`** | 项目级配置与规范文档 | 仅限全局配置（如 `package.json`, `_config.yml`, `_config.fluid.yml`）和全局规范文档（如 `CLAUDE.md`, `AGENTS.md`, `readme.md`）。绝不能放具体业务代码、测试文件、临时记忆或一次性 skill 清单。 |
| **`/source`** | Hexo 内容源 | 所有博客内容存放于此，Hexo 构建时以这里为入口。 |
| ├── `/source/_posts` | 文章 Markdown | 文件名格式 `YYYY-MM-DD-slug.md`，包含 front matter（title, date, categories, index_img 等）。 |
| ├── `/source/images` | 图片资源 | 存放博客文章插图、头像等（如 `my-avatar.jpg`, `img_*.png`），含 `covers/` 子目录。 |
| ├── `/source/admin` | 在线后台页面 | 存放 `index.html`，通过 `/admin/` 访问。 |
| ├── `/source/js` & `/source/css` | 自定义前端脚本和样式 | 存放如 `aoiblog-home.js`、`aoiblog-home.css` 等自定义资源。 |
| ├── `/source/about` | 关于页面 | 存放 `index.md`。 |
| ├── `/source/friends` | 友情链接页面 | 存放 `index.md`。 |
| ├── `/source/guestbook` | 留言板页面 | 存放 `index.md`。 |
| ├── `/source/news` | 每日日报静态页 | 存放 `/news/` 页面和生成数据。`data/` 主要由管线和页面 API 产出；可人工维护 `source/news/data/interest_profile.md` 的兴趣画像要点，其余数据优先通过管线或页面操作生成。 |
| **`/api`** | Vercel Serverless 接口 | 后端业务逻辑。**一个文件对应一个明确的接口职责**。包括后台文章/设置接口，以及日报反馈、稍后读写回接口；`vocab.js` 仅为停用功能保留，非接口逻辑不要放进这里。 |
| **`/tools`** | 迁移和维护工具 | 存放如 `export-articles-to-hexo.mjs` 等一次性或维护脚本。 |
| **`/news-pipeline`** | 每日日报生成管线 | Python 管线、新闻源、评分配置和测试。改日报生成逻辑只在这里动手。 |
| **`/.github/workflows`** | GitHub Actions | 仅存放仓库自动化工作流，例如 `daily-news.yml`。 |
| **`/docs`** | 项目维护文档 | 根层存现行维护规范；`archive/` 只存仍有兼容、迁移或排障价值的历史记录。完成的实施计划和一次性分析报告在结论并入 `readme.md` 后删除。 |

---

## 2. 文件命名规范

为保持代码库的统一性，不同类型的文件采用不同的命名风格：

### 2.1 文章文件 (YYYY-MM-DD-slug)
- **规则**：日期前缀 + 英文 slug，全小写连字符。
- **适用范围**：`/source/_posts/`。
- **示例**：`2026-04-03-markdown-yu-fa-bi-ji.md`。

### 2.2 静态资源 (lowercase / kebab-case)
- **规则**：全小写，单词间用连字符 `-` 连接。因为这些文件名通常直接暴露在 URL 中。
- **适用范围**：`/source/images/`、`/source/js/`、`/source/css/`。
- **示例**：`friend-avatar.jpg`、`aoiblog-home.css`。
- *注：通过工具自动上传生成的图片，保留原时间戳格式即可（如 `img_1774010498471.png`）。*

### 2.3 后端接口文件 (camelCase)
- **规则**：小驼峰命名法，清晰表达接口意图。
- **适用范围**：`/api/` 目录下的 Serverless 函数。
- **示例**：`adminArticles.js`、`adminSettings.js`、`adminUpload.js`、`newsState.js`、`vocab.js`。
- **特殊约定**：内部共享的工具模块，使用下划线前缀以区分对外接口，如 `_github.js`。

### 2.4 文档与配置文件
- **规则**：遵循业界常规（通常为全小写）。
- **示例**：`package.json`、`readme.md`。
- **特殊约定**：最高约束文档保持全大写 `CLAUDE.md` / `AGENTS.md` 以示强调。
- **根目录边界**：不要再新增 `memory.md`、`skill.md` 这类一次性索引；持久规则进入 `AGENTS.md` / `CLAUDE.md`，面向维护者的说明进入 `readme.md` 或 `docs/`。

---

## 3. 文件创建决策指南（当你需要加东西时）

**场景 1：我要发布一篇新文章**
👉 **动作**：在 `/source/_posts/` 下创建 `YYYY-MM-DD-slug.md`，填写 front matter。

**场景 2：我要上传一张说明图，并在文章中引用**
👉 **动作**：将图片放入 `/source/images/`，命名为 `xxx-architecture.png`，确保名字有语义。文章中引用路径为 `/images/xxx-architecture.png`。

**场景 3：我要给后台或日报页增加一个写回功能**
👉 **动作**：在 `/api/` 下创建职责明确的小驼峰文件，例如 `adminSummary.js` 或 `newsState.js`；一个文件只处理一类接口职责。

**场景 4：我要调整每日日报新闻源**
👉 **动作**：修改 `news-pipeline/sources.yaml`；不要直接编辑 `source/news/data/` 下的生成数据。

**场景 5：我要调整每日日报评分、阈值或分类偏好**
👉 **动作**：修改 `news-pipeline/config.yaml`，并运行 `python news-pipeline/tests/test_pipeline.py` 做逻辑回归。

**场景 6：我要人工修正每日日报兴趣画像**
👉 **动作**：修改 `source/news/data/interest_profile.md`，只编辑以 `- ` 开头的偏好要点；不要手工改 `daily/*.js`、`events.json`、`source_health.json`、`feed.xml` 或 `search_index.js`，这些由管线产出或重建。`vocab/*.js` 是已停用单词本的历史数据，也不要手工维护。

**场景 7：我要维护日报反馈或稍后读**
👉 **动作**：优先通过 `/news/` 页面操作，由 `api/newsState.js` 写 `feedback.json` / `read_later.json`；不要绕过 API 直接编辑这些状态文件，除非是在排障时做最小修复。单词本已停用，`api/vocab.js` 与 `vocab-book.json` 仅为恢复能力保留。

**场景 8：我要记录一个 Vercel 部署相关的深坑经验**
👉 **动作**：不要新建文档，直接修改根目录的 `readme.md`；如果是规则边界，再同步 `AGENTS.md` / `CLAUDE.md`。
