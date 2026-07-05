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

`source/news/` 是一个独立的静态"每日新闻驾驶舱"页面，通过导航菜单"日报"访问（`/news/`）。

- 页面与数据均为纯静态文件，`_config.yml` 的 `skip_render: news/**` 保证 Hexo 原样拷贝、不经主题渲染。
- 数据由本仓库 `news-pipeline/daily_news.py` 生成（抓取 → LLM 去重评分摘要 → 写入 `source/news/data/`）。改新闻源改 `news-pipeline/sources.yaml`，调评分口味改 `news-pipeline/config.yaml`。
- **信源结构**（2026-07-04 起）：官方一手源（OpenAI/Hugging Face/DeepMind/GitHub/Cloudflare/Vercel，T1）+ 专业媒体 + 舆论源。硬约束：纯舆论源（`source_type: opinion`，如 Hacker News）支撑的事件分数封顶在精选阈值之下，只能进"更多资讯"，有事实/分析源交叉才解除限制。
- **信源健康度**：管线每次运行把各源抓取状态写入 `source/news/data/source_health.json`（滚动 14 天，区分"抓取失败"与"窗口内无新文章"）；某源连续 3 天抓取失败时在 GitHub Actions 运行页输出 warning 注解。排查时先跑 `python daily_news.py --dry-run` 看各源状态。
- **每日自动更新**：GitHub Actions（`.github/workflows/daily-news.yml`）每天 UTC 23:00（北京 07:00 左右）运行管线，校验通过后自动 commit + push `source/news/data/`，触发 Vercel 部署上线。这是"严禁自动 push"规则的唯一例外，详见 `CLAUDE.md`。
- API key 存于仓库 Secrets（`LLM_API_KEY`），绝不进代码。失败时 GitHub 自动发邮件通知，可在 Actions 页面手动 Re-run 或用 Run workflow 补跑；失败当天线上保持昨日日报。
- 本地手动补跑：`cd news-pipeline && pip install -r requirements.txt && set LLM_API_KEY=你的key && python daily_news.py`（本地产物写到 `news-pipeline/data/`，已 gitignore；如需直接写入站点数据，设 `DATA_DIR` 指向 `source/news/data`）。
- **细粒度主题标签**（2026-07-04 起）：精加工阶段 LLM 从受控词表（`news-pipeline/config.yaml` 的 `topic_tags`）给每条精选选 1-2 个标签，前端在类目 Tab 下按标签过滤。词表外标签一律丢弃；改词表只改配置不动代码。
- **跨天事件追踪**（2026-07-04 起）：管线维护 `source/news/data/events.json` 登记表，每天把今日精选与近 14 天活跃事件做 LLM 延续性匹配（同类目硬校验，拿不准不匹配）。连续出现 ≥2 天的事件在页面卡片上带「📌 第N天」徽标，点击展开此前进展。参数在 `config.yaml` 的 `events` 块：7 天无新进展自动归档（归档后同一故事复燃按新事件重新登记），归档超 60 天从文件删除。降级安全：登记表缺失/损坏冷启动、LLM 匹配失败当天全按新事件处理、同日重跑幂等不重复计天。
- **用户状态写回 API**（`api/newsState.js`）：POST/GET，`ADMIN_TOKEN` Bearer 鉴权，把反馈（`feedback`）和稍后读（`read_later`，op: add/done/remove）追加写入 `source/news/data/feedback.json` / `read_later.json`（各封顶 1000 条，稍后读按 item_id+date 去重）。
- **反馈闭环**（2026-07-05 起）：页面上持有后台 token（`localStorage["aoiblog_admin_token"]`，与 `/admin/` 共用）时，精选卡片出现操作行，访客看到的仍是纯阅读页。四种反馈的去向：
  - 不感兴趣（快捷理由 chips + 可选备注）→ 本地立即隐藏 + 入画像；「只是今天不想看」且无备注的只隐藏不入画像；
  - 更多类似 → 入画像正向信号；稍后读收藏也作为隐式正向信号；
  - 来源质量低（选具体来源）→ **机械降权**：管线运行时按近 90 天有反馈的自然日计次，该来源可信度每次 ×0.9、下限 ×0.7（不改 sources.yaml）；
  - 追踪/取消追踪 → events.json 事件钉选。钉选事件即使不进精选也会出现在页面「📌 追踪中」区（管线会拿它和"更多资讯"补匹配防断档），7 天无进展仍自然归档。
- **兴趣画像**（`source/news/data/interest_profile.md`）：明文 markdown，管线每天把 marker（`<!-- last_feedback_ts -->`）之后的新反馈蒸馏进去，**可以直接手改/删行**（要点行以 `- ` 开头）。画像通过"兴趣契合分"影响排序：每事件乘数 ∈ [0.85, 1.15]，中性 = 1.0；画像为空或蒸馏/拟合失败时一切保持中性，不影响产出。
- **深度阅读频道**（2026-07-05 起）：独立于新闻管线的长文推荐。源在 `sources.yaml` 的 `deep_sources`（AI/LLM 深度 + 科技商业分析，均已验证 RSS 可用；财经深度暂无可用免费 RSS——财新/晚点无 RSS、FT 付费墙，为已知取舍）。参数在 `config.yaml` 的 `deep` 块：LLM 打"深读价值分"，阈值制每天 0-3 篇（宁缺毋滥），英文源生成中文标题+导读，阅读时长按 RSS 全文长度代码估算。已推荐 URL 记录在 `data/deep_seen.json` 防重复推荐。深读频道整体是独立故障域，失败只丢当天推荐、不影响新闻主管线。
- **RSS 订阅**：管线每天生成 `source/news/data/feed.xml`（订阅地址 `/news/data/feed.xml`），每条精选一个 item（含摘要/为什么重要/来源链接），深读推荐带【深读】前缀，收录最近 7 天。channel 链接用 `config.yaml` 的 `site_url`。
- **站内搜索**：管线维护 `source/news/data/search_index.js`（紧凑索引，保留 180 天，缺失时自动从历史 daily 文件全量重建）；页面搜索框懒加载索引，按标题+标签过滤，点击结果跳转到对应日期并高亮该条目。
- **周视图**：纯前端聚合——页面「周视图」按钮加载最近 7 天数据，展示每日 Top3 + 本周事件线（events.json 中跨天≥2天的事件）。
- 回归测试：`python news-pipeline/tests/test_pipeline.py`（纯逻辑，不调 LLM 不联网；改评分/聚类/健康度/事件登记/深读/feed/索引逻辑后必跑）。
- 移除方式：删除 `source/news/`、`news-pipeline/`、`.github/workflows/daily-news.yml`、`_config.yml` 中的 `- news/**`、`_config.fluid.yml` 菜单中的 `news` 项即可完全剥离。
- 历史沿革：管线原为独立项目 `D:\每日新闻网站`（2026-07-04 迁入本仓库并退役）。
