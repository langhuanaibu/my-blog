# Aoitsuki Blog

这是 Aoitsuki 的个人博客项目，当前采用 `Hexo + Fluid + Vercel` 的静态博客架构。

## 当前架构

- 博客框架：Hexo
- 主题：Fluid
- 内容源：`source/_posts/*.md`
- 静态资源：`source/images/`
- 自定义脚本：`source/js/`
- Vercel API：`api/`
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
api/                    Vercel Serverless API
source/about/           关于页面
source/friends/         友情链接页面
source/guestbook/       留言板页面
source/news/            每日新闻日报页（静态，数据由 news-pipeline 生成）
news-pipeline/          新闻日报生成管线（GitHub Actions 每日运行）
tools/                  迁移和维护工具
docs/archive/           历史架构与迁移记录
_config.yml             Hexo 主配置
_config.fluid.yml       Fluid 主题配置
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

## 内容维护

- 在线后台地址是 `/admin/`。登录后可以发布、编辑、删除文章，也可以上传文章封面和正文图片。
- 后台“站点设置”可以修改常用展示文本，包括站点标题、副标题、首页标语、页脚文本、关于页昵称/简介和现有导航显示名。
- 新文章最终会写入 `source/_posts/`。
- 图片统一放入 `source/images/`，文章中使用 `/images/<filename>`。
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

浏览器只保存 `ADMIN_TOKEN`，GitHub token 只保存在服务端环境变量中。

## 修改网站文字

- 站点标题、副标题、首页标语、页脚、关于页昵称/简介、现有导航显示名：优先通过 `/admin/` 的“站点设置”修改。
- 站点描述、域名、语言、构建目录等底层配置：改 `_config.yml`。
- 导航链接、导航图标、头像、背景图、主题开关等主题配置：改 `_config.fluid.yml`。
- 关于页正文：改 `source/about/index.md`。
- 友链页正文：改 `source/friends/index.md`。
- 留言页正文：改 `source/guestbook/index.md`。
- 文章标题、分类、日期、封面、正文：优先通过 `/admin/` 编辑，也可以直接改 `source/_posts/*.md`。

## 发布新文章

推荐方式：

1. 打开 `/admin/`。
2. 输入后台口令。
3. 点击“新文章”。
4. 填标题、日期、分类和 Markdown 正文。
5. 可选上传封面；不上传时使用分类默认封面。
6. 点击“发布”，后台会提交 Markdown 和图片到 GitHub，Vercel 会自动重新部署。

本地方式：

1. 在 `source/_posts/` 新建 Markdown 文件。
2. 图片放到 `source/images/`。
3. 在 front matter 中填写 `title`、`date`、`categories`、`index_img`。
4. 运行 `npm run build` 验证。

## 迁移说明

本项目曾使用 `Astro + Vercel Serverless API + MongoDB + public/admin.html` 架构。

2026-06-18 起迁移为 Hexo 静态博客：

- 线上公开 API 返回的 19 篇文章已迁移为 Markdown。
- 后台草稿未迁移。
- 旧 `/articles.html#article_id` 链接由 `source/articles.html` 兼容跳转到新文章地址。
- Twikoo 评论使用每篇文章的旧 `article_id` 作为 path，尽量保留旧评论关联。
- 旧 Astro 前台、Vercel API 和静态后台不再作为运行入口保留。

详细决策见 `docs/archive/2026-06-18-hexo-fluid-migration.md`。

## 每日日报页（/news/）

`source/news/` 是独立的静态"每日新闻驾驶舱"页面，通过导航菜单"日报"访问（`/news/`）。页面与数据均为纯静态文件，`_config.yml` 的 `skip_render: news/**` 保证 Hexo 原样拷贝、不经主题渲染。

### 数据管线

- 主管线是 `news-pipeline/daily_news.py`：抓取 RSS / AI HOT → 预筛 → LLM 去重聚类、分类、五维打分 → 代码合成最终分 → 生成摘要、事件追踪、深读推荐、RSS 和搜索索引。
- 改新闻源优先改 `news-pipeline/sources.yaml`；调评分、阈值、标签词表、事件追踪、深读、RSS 和搜索保留窗口优先改 `news-pipeline/config.yaml`。
- 信源分为官方/事实源、分析源、舆论源，并有 T1 / T1.5 / T2 层级。纯舆论源（`source_type: opinion`）支撑的事件分数会封顶在精选阈值之下，只能进"更多资讯"；有事实源或分析源交叉佐证后才解除限制。
- 精选采用阈值制，不硬凑固定条数；同时保留类目保底、上限、同源封顶和受控主题标签。主题标签只允许来自 `config.yaml` 的 `topic_tags`，词表外标签会被丢弃。

### 自动运行与本地运行

- GitHub Actions（`.github/workflows/daily-news.yml`）每天 UTC 23:00（北京 07:00 左右）运行管线，校验通过后自动 commit + push `source/news/data/`，触发 Vercel 部署上线。这是"严禁自动 push"规则的唯一例外，详见 `CLAUDE.md`。
- API key 存于仓库 Secrets（`LLM_API_KEY`），绝不进代码。失败时 GitHub 自动发邮件通知，可在 Actions 页面手动 Re-run 或用 Run workflow 补跑；失败当天线上保持上一份已生成日报。
- 本地手动补跑：`cd news-pipeline && pip install -r requirements.txt && set LLM_API_KEY=你的key && python daily_news.py`。默认产物写到 `news-pipeline/data/`（已 gitignore）；如需直接写入站点数据，设置 `DATA_DIR` 指向 `source/news/data`。
- 排查信源抓取时先跑 `python daily_news.py --dry-run`，只抓取、不调 LLM。

### 线上数据产物

`source/news/data/` 是线上数据目录，大多数文件由管线或后台 API 创建，不应手工改写，除非下方明确允许。

- `daily/YYYY-MM-DD.js`：每日页面数据。
- `manifest.js`：日报日期清单。
- `source_health.json`：信源健康度，滚动保留 14 天，区分"抓取失败"与"窗口内无新文章"；某源连续 3 天抓取失败时在 Actions 输出 warning。
- `events.json`：跨天事件登记表。管线把今日精选与近 14 天活跃事件做延续性匹配；连续出现 2 天及以上的事件会在页面显示跨天徽标。7 天无新进展自动归档，归档超 60 天删除；文件缺失或损坏时冷启动重建。
- `feedback.json` / `read_later.json`：由 `api/newsState.js` 写入，分别保存反馈和稍后读状态，各封顶 1000 条。稍后读按 `item_id + date` 去重。反馈支持删除式撤销：payload 带 `op: "remove"` 时删除最后一条同 `date + item_id + action` 的记录（页面「更多类似」再点一次即撤销）；管线当晚已蒸馏进画像的部分不回滚，需手改 `interest_profile.md`。
- `interest_profile.md`：兴趣画像，管线会把 marker（`<!-- last_feedback_ts: ... -->`）之后的新反馈蒸馏进去。这个文件可以人工编辑或删行，但偏好要写成以 `- ` 开头的要点。
- `deep_seen.json`：深度阅读推荐 URL 去重记录，按配置保留。
- `feed.xml`：RSS 订阅文件，地址为 `/news/data/feed.xml`，按 `config.yaml` 的 `feed_days` 收录精选，深读推荐带【深读】前缀。
- `search_index.js`：站内搜索紧凑索引，缺失时可由管线从历史 daily 文件重建。

### 页面能力

- 页面视觉与博客羊皮纸主题统一，亮/暗跟随博客：初始化读 Fluid 写入的 `localStorage["Fluid_Color_Scheme"]` 决定亮暗，未设置则跟随系统。耦合点：博客若更换主题或改这个存储键，日报页暗色会静默失效。
- 页面持有后台 token（`localStorage["aoiblog_admin_token"]`，与 `/admin/` 共用）时，精选卡片显示反馈操作；普通访客看到的仍是纯阅读页。
- 反馈包括不感兴趣、更多类似、来源质量低、追踪/取消追踪。来源质量低会在后续管线运行中按近 90 天反馈自然日机械降权，不修改 `sources.yaml`。
- 卡片上的稍后读、更多类似、追踪都是可撤销开关，再点一次即撤回对应记录。
- 追踪事件即使不进精选，也会出现在页面的追踪区；管线会用"更多资讯"补匹配，尽量防止断档。
- 深度阅读频道独立于新闻主管线，源来自 `sources.yaml` 的 `deep_sources`。深读失败只丢当天深读推荐，不影响新闻日报产出。
- 周视图为纯前端聚合：加载 7 天窗口数据，展示每日 Top3 和跨天事件线。

### 验证与移除

- 回归测试：`python news-pipeline/tests/test_pipeline.py`。该测试不调 LLM、不联网；改评分、聚类、健康度、事件登记、偏好学习、深读、RSS 或搜索索引逻辑后必跑。
- 移除方式：删除 `source/news/`、`news-pipeline/`、`.github/workflows/daily-news.yml`、`_config.yml` 中的 `- news/**`、`_config.fluid.yml` 菜单中的 `news` 项即可完全剥离。
- 历史沿革：管线原为独立项目 `D:\每日新闻网站`，已在 2026-07-04 迁入本仓库并退役。
