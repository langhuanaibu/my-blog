# Aoitsuki Blog

这是 Aoitsuki 的个人博客项目，当前采用 `Hexo + Fluid + Vercel` 的静态博客架构。

## 当前架构

- 博客框架：Hexo
- 主题：Fluid
- 内容源：`source/_posts/*.md`
- 静态资源：`source/images/`
- 自定义脚本：`source/js/`
- Vercel API：`api/`（在线后台、日报反馈与稍后读写回；停用的单词本接口仍保留）
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
tools/                  迁移和维护工具
docs/                   维护规范与必要的历史记录
docs/archive/           历史架构与迁移记录（非当前运行说明）
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

新闻页前端回归测试：

```powershell
npm run test:news
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

`ADMIN_TOKEN` 只在当前后台页面的内存中使用，刷新后台后需要重新输入，不会写入 `localStorage`。登录同时换取一个 8 小时有效、`HttpOnly + Secure + SameSite=Strict` 的签名会话，供日报反馈、收藏和稍后读使用；签名会话不具备文章、设置或上传接口的权限。GitHub token 始终只保存在服务端环境变量中。

### API 鉴权与并发保护

- `POST /api/adminSession` 校验后台口令并建立个人会话；`GET` 用于探测会话，`DELETE` 用于退出。会话 Cookie 仅作用于 `/api`，接口不开放跨域凭据读取。
- `api/newsState.js` 只接受个人会话，用于日报反馈、收藏和稍后读；`adminArticles.js`、`adminSettings.js`、`adminUpload.js` 等高权限接口仍要求 `Authorization: Bearer <ADMIN_TOKEN>`。
- 编辑或删除文章时必须提交打开文章时返回的 GitHub blob SHA；文件已被其他操作修改时接口返回 `409`，应刷新后重新编辑，不能覆盖较新的内容。
- 站点设置涉及 `_config.yml` 与 `_config.fluid.yml` 时通过单个 Git commit 原子更新；任一源文件版本过期都会拒绝整次更新，不留下半套配置。

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
- Twikoo 评论使用每篇文章的旧 `article_id` 作为 path，尽量保留旧评论关联。
- 旧 Astro 前台、旧 MongoDB API 和静态后台不再作为运行入口保留；当前 `api/` 是后来建设的在线后台与日报状态接口。

详细决策见 `docs/archive/2026-06-18-hexo-fluid-migration.md`。

## 每日日报页（/news/）

`source/news/` 是独立的静态"每日新闻驾驶舱"页面，通过导航菜单"日报"访问（`/news/`）。页面与数据均为纯静态文件，`_config.yml` 的 `skip_render: news/**` 保证 Hexo 原样拷贝、不经主题渲染。

### 数据管线

- 主管线是 `news-pipeline/daily_news.py`：抓取（RSS / AI HOT / 逐源直连适配器）→ 跨日 URL 去重与重大更新判定 → 预筛 → LLM 去重聚类、分类、五维打分 → 多条事件凝聚度审计 → 代码合成最终分（含热榜 co-occurrence 公众热度加权）→ 精选深加工与事实支撑审计 → 生成今日主线、事件追踪、深读推荐、今日论文（HF Daily Papers）、舆论观察、RSS 和搜索索引。
- 改新闻源优先改 `news-pipeline/sources.yaml`；调评分、阈值、标签词表、事件追踪、深读、精选长叙述（`detail`）、RSS 和搜索保留窗口优先改 `news-pipeline/config.yaml`。
- **信源接入采用"逐源直连适配器"路线**（参考 AIHOT 的做法：RSS 优先、没 RSS 就直连公开接口/网页内嵌数据，不建万能适配层）。三类接法并存：①标准 RSS（`fetch_rss`）；②自建 RSSHub 实例（Vercel）转 RSS——当前用于科学网、澎湃热门、果壳、Anthropic news/engineering 和财联社·深度等已验证路由，`url` 写占位符 `{rsshub}/路由`，运行时由环境变量 `RSSHUB_BASE` + `RSSHUB_KEY` 拼真 URL（地址密钥不落公开仓库，`resolve_rsshub_sources`，主管线与 `deep_sources` 均支持；未配置则自动跳过）；③专用适配器——`fetch_aihot`（JSON API）、`fetch_thepaper_list`（澎湃频道页 `__NEXT_DATA__` 内嵌数据，各 `list_*` 频道同构可复用）、`fetch_weibo_hot`（genvisitor 访客握手，无需登录/浏览器）、`fetch_bilibili_hot`（公开接口）。**不再扩 RSSHub 路由、不上 Docker**。已关闭的信源线（原因见 `sources.yaml` 尾部终局结论注释）：微信公众号（需常驻中继+人肉续期）、知乎（无登录态全线 4xx）、中青报/界面（JS 壳站）、X 直连（AI 类经 AIHOT 二手接入），以及 2026-07-16 验收停用的 FT 中文网和第一财经。
- 主管线在增加任何信源前，必须先观察现有源至少 14 天：抓取成功/零更新、候选与入选量、单源高风险率、独立证据链和来源集中度。`source_health.json` 逐源记录抓取条目、参与评分事件和参与最终精选事件；objectivity shadow summary 记录高风险单源、独立链和来源引用集中度。观察期内不加源、不回填历史数据，数据与人工审查都支持时才可重议。
- 信源分为官方/事实源、分析源、舆论源，并有 T1 / T1.5 / T2 层级。纯舆论源（`source_type: opinion`）支撑的事件分数会封顶在当日有效精选阈值之下，只能进"更多资讯"，也不进入动态阈值账本；有事实源或分析源交叉佐证后才解除限制。
- 抓取健壮性：`fetch_rss`/`fetch_aihot` 统一走 `http_get`（指数退避重试），治 AIHOT 连接重置这类偶发失败——单次请求一挂整源归零。`max_per_source` 默认 18（削减 world/舆论刷屏源的 triage 噪音）；AIHOT 是 AI 深度独木、已精选噪音低，在 `fetch_aihot` 内单独放宽取量、不受该值压制。AI 一手供给以逐篇新闻站（The Decoder 等）为主，不用摘要型 newsletter（每期一条不适配事件聚类）。`source_health.json` 将抓取错误与窗口内零更新分开记录；2026-07-16 验收中，`ftcn` 连续 6 天抓取失败，`yicai` 上游头条接口停留在 2026-05-30，二者均已在 `sources.yaml` 停用。
- 精选采用按产出日等权的动态阈值：每个历史日先对非纯舆论事件最终分计算 nearest-rank P75，再取最近 14 个有效日值的中位数并钳制到 66-82；不足 5 日或账本异常时回退静态 68。五类各有 3 个保留席，优先取过线事件，不足时只从“有效阈值−8”以上补位；`pick_min: 8` 也遵守同一质量线，宁可少发。保留席不参与最终按分截断，精选硬顶为 32；可选 `max_per_category` 当前为空，但启用时优先于保留席。AI 与其他类目仍按分竞争，`TRIAGE_SYSTEM` 首轮未改。主题标签只允许来自 `config.yaml` 的 `topic_tags`。
- 可信度质量门分两层：跨批次聚类后，所有含两个及以上原始条目的事件都会复核凝聚度；审计输出无效或调用失败时，该事件拆回单条、取消多源加成并把证据分降为中性值。精选深加工后再核对 `why/context/significance/watch/detail/claims` 是否由当前事件来源支撑；审计失败时保守删除全部扩展字段，只保留标题、摘要、来源、分类、状态、分数和时间等基础内容，避免未经复核的叙述进入日报。
- 面向读者的生成文字（精选 title/summary/why/context/detail 与今日主线）受 prompt 层"客观性规范"约束（2026-07-18 起）：只陈述可追溯事实，媒体的立场性定性必须显式归因（"X 报道称"）、不得写成事实，剥离情绪化措辞与无依据动机推断，禁止为"平衡"编造原文没有的对立观点；立场性判断优先进 `claims`（kind=analysis）。
- 精选深加工按字段分工生成：`summary` 写事实增量，`why` 写公共影响和利害关系，`context` 承载「来龙」，`significance` 给画像相关的学习/行动参考，`watch` 承载「走向」，`detail` 串联来源已有的因果过程和关键细节，`claims` 只承载需要显式归因的分析或不确定判断。走向最多 90 字，需说明 1-2 个关键变量并给出至少一个可观察路标；禁止具体概率、无条件断言和来源外类比，支撑审计删除后不填充占位内容。interim、shadow、active 共用同一字段裁剪策略。prompt 会显式携带 `category`：非 AI 类补必要术语和机构背景，AI 类直接进入增量；机制链、数字比较和利益相关方只在来源支持时选最有价值的一至两项，不为追求深度补写来源外事实。该行为仍使用 interim 摘要输入，五日人工质量验收记在 `docs/news_source_roadmap.md`。
- **公开路径当前只到这一层**：`config.yaml` 的 `objectivity.mode` 默认 `interim`，只启用上述 prompt 规则和原有的 support-only 事实支撑审计。完整正文取证、独立证据链佐证、客观性定向修复/降级/降档的代码已经存在，但只在 shadow 或未来的 `active` 模式下运行；**`active` 尚未启用，线上验收尚未完成**。审计模型可用 `config.yaml` 的 `audit_llm` 段单独指定，留空则继承 `llm`。
- 完整模式的证据合同是 `evidence: {basis, publisher_count, independent_chain_count, degraded}`（`basis` 取 `fulltext|mixed|snippet`）；来源可带 `evidence_basis`/`evidence_chain`，claims 用 `sources` 标注归因，`degraded` 表示摘要退化或修复失败后的保守内容，高风险事件复审仍失败会从精选降到"更多资讯"。前端只在结构完全合法时渲染证据概览，旧数据静默降级。正文只是当次运行内存中的审计证据（每源上限 4000 字），不写入日/周报、feed、search、registry、profile、health 或 vocab 等任何数据文件；抓取器不登录、不执行页面脚本、不绕过付费墙，取不到就退回 RSS 摘要。
- 验收门槛、安全边界和统计口径见 `docs/news_objectivity_plan.md`：切 `active` 前必须同时通过 7 天线上指标门和 45 条夹具的三轮门，并另行人工评审。
- AI HOT 条目会带上其原生分类（模型/产品/论文/技巧）作为 `tag_hint`，在阶段 B 打标时优先入选，保证「研究论文」「技巧观点」这类内容不被大类淹没——前端现有子标签筛选即可单独筛出，无需改前端。
- 兴趣画像影响排序：`interest_profile.md` 非空时，管线对每个事件打"兴趣契合分"换算成分数乘数，幅度由 `config.yaml` 的 `scoring.fit_span` 控制（默认 ±0.30，画像明确不关注的事件被压低、更关注的被抬高）。
- 画像含手写的「## 学习参考系」段（长期学习方向/当前能力栈/希望积累的判断力/资讯转化偏好）：阶段B 据此把每条精选的"对我的意义"（`significance`）写成学习路线导向的**可操作参考**（该补什么概念、读什么文档/论文、试什么工具、盯什么能力趋势），无可操作关联则留空。该段每晚蒸馏时由 `split_section` 摘出、绕过 LLM、原样贴回（`update_profile`），不会被自动改写冲掉；旧的「## 我的处境」段仍会被兼容保护。
- 长尾去噪：预筛除丢弃硬垃圾外，还会给"软边角料"（体育赛果、明星八卦、猎奇轶闻、日抛热点）打标；整条来源都是软标记的事件不进"更多资讯"（不影响精选）。"更多资讯"条数由 `secondary_count` 控制（默认 8，真·漏网提醒）。

### 自动运行与本地运行

- GitHub Actions（`.github/workflows/daily-news.yml`）每天 UTC 23:00（北京 07:00 左右）运行管线，校验通过后自动 commit + push `source/news/data/`，触发 Vercel 部署上线。这是"严禁自动 push"规则的唯一例外，详见 `CLAUDE.md`。
- API key 存于仓库 Secrets（`LLM_API_KEY`），绝不进代码。自建 RSSHub 源另需两个 Secret：`RSSHUB_BASE`、`RSSHUB_KEY`（未配置则相关源自动跳过，管线不崩）。LLM 模型用显式版本名 `deepseek-v4-flash`（`deepseek-chat` 别名 2026-07-24 官方停用）；V4 裸模型名默认开 thinking 模式（temperature 静默失效、思考 token 计费），管线经 `config.yaml` 的 `llm.extra_body` 显式关闭，换供应商时删掉该配置即可。失败时 GitHub 自动发邮件通知，可在 Actions 页面手动 Re-run 或用 Run workflow 补跑；失败当天线上保持上一份已生成日报。
- 本地手动补跑（PowerShell）：始终在仓库根目录运行 `py -3.12 -m pip install --require-hashes -r news-pipeline/requirements.txt`，再用 `$env:LLM_API_KEY="你的key"` 注入密钥并执行 `py -3.12 news-pipeline/daily_news.py`。需要抓自建 RSSHub 源时再设置 `$env:RSSHUB_BASE` 和 `$env:RSSHUB_KEY`。默认产物写到 `news-pipeline/data/`（已 gitignore）；如需直接写入站点数据，设置 `$env:DATA_DIR` 指向 `source/news/data`。
- 客观性 shadow：`python news-pipeline/daily_news.py --objectivity-shadow`。它先把当前 `DATA_DIR`（含 feedback/profile/registry/weekly 等状态）整树复制到临时快照，读写只发生在快照里，正常返回、提前返回、异常和校验失败都会还原环境并删除快照；输出只有不含正文和密钥的聚合指标，包括高风险单源数量/比率、独立链和来源集中度。Actions 里的 `shadow` job 在 `generate` 成功后重新 checkout `main` 运行，限时 24 分钟、只读、允许失败，不 commit/push，也不改动已发布的日报。generate 的 step summary 另记录当日阈值来源、质量线、类目供给/入选和过线次级事件数。
- 客观性模型验收：`python news-pipeline/objectivity_eval.py`。语料固定为仓库内 45 条夹具（`news-pipeline/fixtures/`，受 canonical JSON 的 SHA-256 约束，不能用 CLI 换），每条先走生产 `enrich` 与完整 audit/repair/fallback，再交独立 judge 评分；生成模型和 judge 都拿不到夹具分类、预期标签和验收阈值。只有显式配置了线上 LLM 凭证才会连跑三轮，并按最差一轮决定退出码。自动化测试只用本地桩，不调付费接口。
- 顶层 Python 依赖维护在 `news-pipeline/requirements.in`，使用与 Actions 一致的 Python 3.12 在仓库根目录运行 `py -3.12 -m piptools compile --generate-hashes --resolver=backtracking --output-file news-pipeline/requirements.txt news-pipeline/requirements.in`。`sgmllib3k` 使用 `news-pipeline/vendor/` 内受控 wheel，生成后必须保持锁文件中的仓库相对路径并运行一次 `pip install --dry-run --require-hashes`，不能退回会动态下载构建工具的源码包。
- 排查信源抓取时先跑 `py -3.12 news-pipeline/daily_news.py --dry-run`，只抓取、不调 LLM。
- 若通过 `publish.blog_dir` 把独立数据目录同步到博客，管线会完整镜像整个 `data/` 树并清理目标中的陈旧派生文件；切换使用临时目录和备份，失败时恢复旧目录，后续运行也会先恢复遗留备份。只有日报成功生成后才会进入发布同步。

#### 选材与可信轨迹并行上线门

- 每次登记表阶段输出一行「轨迹健康」，稳定记录候选匹配、连续性通过/拒绝、被排除的历史行、整条生成回退、审计字段/claim 回退，以及最终公开走向数/精选数和覆盖率。连续性响应缺失或非法时按拒绝计数，其历史全部计入过滤；生成回退按条目计，审计回退按未采用的字段或 claim 计。
- 离线冒烟夹具是 `news-pipeline/fixtures/trajectory_rollout.json`，固定包含一条可信延续、一条污染历史和一条缺少精确 `item_ref` 的旧行；运行 `python news-pipeline/tests/test_trajectory_rollout.py` 不联网、不依赖额外测试包，也不写 `source/news/data/`。常规 `python news-pipeline/tests/test_pipeline.py` 会同时执行这组回归。
- 本轮未宣称已部署或线上验收通过。获得公开启用授权后，选材改革与可信轨迹**同日公开**，不再等选材先跑完。两门从首个有效输出日起独立连续计数：选材 7 日，轨迹 5 日。轨迹每天的全量初验复用 `audit_llm` 连接/模型配置并强制 `temperature: 0`；模型、schema 或评审基础设施异常一律记 `needs_review`，留给人工最终确认，不猜测通过。
- GitHub Issue #15 是这两门的**唯一自动每日台账**。同一北京日期的重跑只幂等更新当日记录，不多算一天；当日任一次发布失败，即使后续重跑成功，当日两门仍都按失败处理。非发布失败时，`pass` 让对应门 +1，`fail` 只把对应门清零，`neutral` / `needs_review` 冻结该门当前计数。
- 观察期冻结选材运行逻辑和轨迹展示逻辑；必须改动时按影响范围重计。选材/共享运行时指纹变化会同时重置两门，只有轨迹 UI 指纹变化则仅重置轨迹门；发布失败也同时重置两门。自动初验失败、`needs_review` 或台账写入异常只在 Actions/Issue 告警，不阻断日报发布、不改配置、不自动回滚。两门分别达到 7/5 日时只标记「待人工最终确认」，不自动关闭 #15 或 #10。
- 每天人工检查全部可信延续，并额外抽查 5 条覆盖不同类目的一次性精选；5 个有效输出日内错误串线、无依据历史/判断、错误延续跳转和主管线发布失败都必须为 0。对全部已展示 `watch` 做质量抽样，至少 80% 同时包含具体关键变量和可观察路标；另记走向覆盖率、轨迹回退率和历史行过滤率，不为提高覆盖率放宽连续性或审计门。
- enrich 五日文字质量门、客观性 shadow 七日门 + 45 条夹具三轮门、主管线信源 14 日观察门仍然独立有效，不被选材/轨迹计数替代。前三个受选材样本或新观测字段影响的时钟，均从并行公开后首个有效输出日重计；enrich 安全基线取新窗口前 3 个输出日中位数，客观性固定夹具门和独立深读源观察不重计。
- 是否回滚由人工根据当日证据决定。轨迹回滚时把 `news-pipeline/config.yaml` 的 `trajectory.enabled` 改为 `false` 后重新生成：连续性验证和登记表兼容更新仍保留，但跳过轨迹生成，公开 payload 标记关闭并移除来龙、走向与延续投影。恢复时改回 `true`；`events.json` 的 v2 可选字段无需迁移或回滚，既有日报数据也不重写。选材参数回退口径见 `docs/news_selection_plan.md`。

### 线上数据产物

`source/news/data/` 是线上数据目录，大多数文件由管线或后台 API 创建，不应手工改写，除非下方明确允许。

- `daily/YYYY-MM-DD.js`：每日页面数据。顶层 `quality` 记录审计事件数、拆分数、删除字段数、跨日重复数、重大更新数、更新判定失败数和是否发生降级；`trajectory_enabled` 是当日轨迹展示开关；`themes` 为"今日主线"（2-3 条，每条含 `member_ids` 引用当日 `pick-N`/`more-N` 条目，可跨精选与更多资讯）。每条精选还可带 `context`（来龙）、`watch`（走向）、`significance`（对我的意义，结合兴趣画像生成）、`detail`（中文长叙述，约 300-600 字，由 `config.yaml` 的 `detail` 段控制）和 `claims`（0-4 条需归因的分析或不确定判断，形如 `{text, kind: analysis|uncertain, sources: [来源名]}`，可缺省或为空；读取端继续兼容旧数据的 `kind: fact`）；同 URL 出现实质信息增量时还会带 `is_update: true` 与 `first_seen`，页面明确标注“重大更新”。这些扩展字段只有通过事实支撑审计才会保留。深读条目带 `key_points`（≤3 条）/`audience`/`takeaway`，论文条目带 `contribution`/`evidence`/`limitations`/`takeaway`，供详情页渲染。旧数据缺少新字段时前端静默降级。
- `manifest.js`：日报日期清单。
- `quality-health.json`：滚动保留最近 90 天的日报可信度审计统计，并汇总审计事件数、拆分数与拆分率，用于观察错误聚类趋势；同日重跑会覆盖当日记录。
- `source_health.json`：信源健康度，滚动保留 14 天；保留 `count/error` 区分抓取失败与窗口内无新文章，并记录逐源 `scored_events/selected_events`。某源连续 3 天抓取失败时在 Actions 输出 warning。
- `score_history.json`：动态精选线内部账本（v1），按日期保存非纯舆论事件的最终分，同日重跑覆盖并保留最近 30 个产出日。阈值只读取当天之前的数据；账本损坏或写入失败会 warning 并回退静态线，原子写入不会遗留临时文件。
- `events.json`：跨天事件登记表（v2，兼容读取 v1）。管线先把今日精选与近 14 天活跃事件做候选匹配，再用独立连续性门同时核对具体事件主线、最近可信进展，并逐行验证最近 7 条历史；同类目本身不构成延续，模型声称匹配最近进展时最新历史行也必须验证通过。只有验证通过的旧行参与公开 `day_count/history`，并进入独立批量轨迹生成和轨迹审计；审计只检查新写的 `context/watch/claims`，字段拒绝时退回当天已经审计的精加工内容，不改变精选层级；整条生成或审计失败时则按一次性事件展示，不输出来龙或延续入口。旧 `watch` 与证据足够时，来龙可用 `兑现/部分兑现/未兑现/反转` 回对上一期走向；证据不足不输出结论。历史行保存轨迹审计后的最终 `watch`、来源标识和 `日期:item_id` 引用，旧行缺少这些字段时仍可读取。同日重跑优先按稳定条目引用替换当日行，即使首日标题修正也保留 `event_id`。整次登记更新先在内存完成；最终日报写入并校验成功后才原子提交 `events.json`，此前任一步失败都会保留上一份完整登记表。7 天无新进展自动归档，归档超 60 天删除，文件缺失或损坏时冷启动重建。
- `feedback.json` / `read_later.json` / `favorites.json`：由 `api/newsState.js` 写入，分别保存反馈、稍后读和 ⭐ 收藏状态，各封顶 1000 条。稍后读/收藏按 `item_id + date` 去重；收藏只存 `date + item_id` 引用（外加 title/category/url 兜底字段，url 可缺省），收藏页凭引用从 `daily/*.js` 重渲染完整卡片，管线暂不消费 favorites。反馈支持删除式撤销：payload 带 `op: "remove"` 时删除最后一条同 `date + item_id + action` 的记录（页面「更多类似」再点一次即撤销）；管线当晚已蒸馏进画像的部分不回滚，需手改 `interest_profile.md`。
- `interest_profile.md`：兴趣画像，管线会把 marker（`<!-- last_feedback_ts: ... -->`）之后的新反馈蒸馏进去。这个文件可以人工编辑或删行（也可一次性手写丰富的种子画像），但偏好要写成以 `- ` 开头的要点。画像既影响精选排序（兴趣契合分），也用于生成每条精选的"对我的意义"。
- `deep_seen.json`：深度阅读推荐 URL 去重记录，按配置保留。
- `deep_health.json`：最近 14 天深度阅读健康度（v2），按源区分抓取成功/失败、窗口内抓取量、去重后候选、已评分、主题匹配、过线和入选；即使当日零候选也会留记录，避免把低频源误判为失效源。
- `papers_seen.json`：今日论文（HF Daily Papers）推荐去重记录，按 `config.yaml` 的 `papers.seen_keep_days` 保留。
- `vocab/YYYY-MM-DD.js` / `vocab-book.json`：**单词本功能已于 2026-07-10 停用**（`config.yaml` 的 `vocab.enabled: false`，管线不再每日挑词；前端界面已移除）。历史数据文件与 `api/vocab.js` 接口原地保留，想恢复时把 enabled 改回 true、前端从 git 历史找回单词本界面即可。
- `feed.xml`：RSS 订阅文件，地址为 `/news/data/feed.xml`，按 `config.yaml` 的 `feed_days` 收录精选，深读推荐带【深读】前缀。
- `search_index.js`：站内搜索紧凑索引，缺失时可由管线从历史 daily 文件重建。
- `news-seen/YYYY-MM-DD.json`：普通新闻跨日去重账本，按日分片并滚动保留 90 天；同 URL 仅时间戳刷新时会在进入任何当日视图前过滤，标题或摘要变化后才交给模型判断是否为重大更新。账本缺失或损坏时从 `all/` 历史档案恢复，且只在日报通过发布校验后写入当天分片。
- `all/YYYY-MM-DD.js` + `all/manifest.js`：全量轻档——抓取窗口内通过跨日去重的全部条目轻字段（标题/链接/来源/类别/时间），滚动保留 90 天。评分阶段结束后 `backfill_all_scores` 按 URL 把事件分回填到匹配条目（被预筛砍掉的无分）；payload 带 `min_score`（`config.yaml` 的 `all_view_min_score`，默认 40），前端默认只显示达标条目、可切换显示全部。两步均独立故障域，失败只记日志、不阻断主管线。

### 页面能力

- 新闻页是无前端框架、无打包步骤的原生 ES Modules 页面：`source/news/index.html` 只保留语义骨架，样式位于 `source/news/news.css`，路由、数据加载、视图和个人操作拆在 `source/news/js/`。现有 `window.NEWS_*` 全局数据脚本继续兼容；数据加载器只接受真实的 `YYYY-MM-DD` 日报日期和 `YYYY-Www` 周报编号，避免 URL 参数被解释为任意脚本路径。
- 页面采用共享响应式外壳：桌面端使用固定左侧栏承载站点标识和 **时间线**、**全部动态**、**报告**、**主题**主导航；移动端使用站点栏、横向主导航和报告归档栏组成的多层顶部导航。裸地址和未知视图默认进入 manifest 最新一期日报；有效个人会话下追加 **收藏**，并显示全局稍后读入口。规范路由为 `?view=timeline`、`?view=all`、`?view=reports&period=day&date=YYYY-MM-DD`、`?view=reports&period=week&week=YYYY-Www`、`?view=topics`、`?view=favs`，旧 `view=picks/day/week` 地址会自动映射。未登录用户直达收藏路由时保留 URL 并显示登录提示，不回退或伪装成时间线。跨天条目统一使用 `日期:id` 复合引用键，反馈、收藏、稍后读和主题追踪按条目或事件最近出现日期记账。
- 新闻页虽然不继承 Fluid 导航，但始终保留博客出口：桌面端左侧栏底部显示“← 返回博客”，移动端站点栏显示首页图标，均以普通 `href="/"` 在当前标签页返回博客首页。该链接不带 `data-route`，避免被日报内部客户端路由接管。
- 时间线视图：按发布时间连续倒序呈现不折叠的单列时间轴，以北京时间日期节点分隔，日期统一显示为中文月日与星期，今天和昨天增加相对前缀；条目按原文发布时间转换为北京时间后归日，日报文件日期只代表生成批次，无有效发布时间时显示「时间待确认」。跨天事件有实质新增时保留在原时间位置并标「延续」，纯重复报道合并来源。顶部「今日主线」是只取最新日报事件的轻量提示，按独立信源、分数和 36 小时时间衰减选出最多 3 条；页内检索与普通时间轴采用相同归日和去重口径。
- 全部动态视图：按日期节点使用倒序单列时间轴，提供文本搜索、来源筛选、分类筛选和评分过滤。回填评分的日子默认只显示 `score >= min_score` 的条目，并提示已隐藏条数，可切换显示低分或未评分内容；条目同时展示来源、分类和分数。
- 报告视图：桌面端显示日/周切换与归档控制栏；移动端顶部栏横向排列周期、归档和前后日期控制。日报正文按 AI、互联网/科技、财经、社会、国际五类稳定分节并全部展开；日报和时间线卡片直出摘要、「为什么重要」，并仅在 `watch` 存在时追加「走向」。可信延续在日报卡片显示可聚焦的「第 N 天·延续」链接：优先跳到上一条精确详情，旧历史缺少 `item_ref` 时降级到对应日期的日报。来龙、对我的意义和 claims 只在详情页展开。「追踪中」紧跟新闻分节，深读、论文、舆论观察和更多资讯依次置后。周报按周主线、数字盘点、动态主题、判断回收、值得读和下周信号纵向展开。
- 主题视图（所有访客可见，URL `/news/?view=topics` 可直达分享）：优先纵向呈现 📌 追踪中、🔥 进行中和 🗄 已归档事件，卡片可展开事件历史进展并回链对应日报，有效个人会话下可追踪或取消追踪。下方「题材地图」使用紧凑自适应网格陈列受控标签及 180 天精选条数，点击进入对应 `tag:` 时间线。
- 全站历史搜索在桌面端常驻内容工具栏；移动端由顶部搜索按钮打开全屏覆盖层，支持关闭按钮与 `Escape` 返回触发按钮。
- 页面视觉采用暖纸色上的报刊编辑风，亮/暗跟随博客：初始化读 Fluid 写入的 `localStorage["Fluid_Color_Scheme"]` 决定亮暗，未设置则跟随系统。阅读型日报、周报、时间线和详情页统一使用 780px 阅读栏；正文条目以栏线分隔，今日主线、深读和结论使用双线特稿框。日报刊头的导语是页面唯一 `h1`，日期使用 `<time datetime>`，装饰印章不进入无障碍树；期号按日报日期的年内日序生成 `YYYY · 第DDD期`，不依赖 manifest 数量。supplementary 栏目通过内部 `data-kind` 区分版式，仅在正文容器达到 740px 时让追踪、论文和更多资讯启用双栏，深读和舆论观察始终单栏。五类颜色仅用于分类文字和栏目题花，事实状态继续使用独立语义色。新增装饰统一使用 `--ink`、`--vermilion`、`--rule` 等 token，暗色模式只覆盖 token。耦合点：博客若更换主题或改这个存储键，日报页暗色会静默失效。
- 视觉回归基准位于 `docs/visual-baselines/news-editorial/`，覆盖时间线、日报、周报、详情、全部动态、主题和收藏七种状态，各保留 1440px 亮色与 390px 暗色截图。它们用于人工对比版式，不参与运行时加载。

#### 新闻页衬线字体

- `source/news/fonts/noto-serif-sc-700/` 是 Noto Serif SC Bold 2.003 的高频字子集，只用于刊头、标题、栏目名和数字；字符清单由已提交新闻 UI 与日报/周报语料中频率最高的 600 个汉字、ASCII 和常用标点组成，子集外字符回退到系统宋体。完整 WOFF2 冷传输为 433,508 字节。源字体来自 Noto Serif CJK 官方 `Serif2.003/14_NotoSerifSC.zip`，`NotoSerifSC-Bold.otf` 的 SHA-256 为 `24693D48BDB9152F0A06B02AF625638A1097ABD6DE4010EBBA027F6E82710527`。OTF 不入库，分发目录保留 `OFL.txt`。
- 再生成时先在固定仓库状态运行 `node tools/font-subsets/build-news-serif-chars.cjs`，再在临时目录安装固定版本 `cn-font-split@7.4.3`，把其 `node_modules` 放入 `NODE_PATH`，然后运行 `node tools/generate-news-font.cjs <NotoSerifSC-Bold.otf> tools/font-subsets/news-serif-sc.txt source/news/fonts/noto-serif-sc-700`。生成后复制官方 `LICENSE` 为输出目录的 `OFL.txt`，并删除工具生成的 `index.proto`。该版本 CLI 的重复 `--subsets` 参数在 Windows 上存在解析问题，因此使用同版本 Node API；脚本显式结束一次性进程以避开生成完成后的 FFI 清理崩溃。
- **统一详情页**与各列表视图共用同一套导航、搜索、主题切换和稍后读外壳，路由使用 `/news/?date=YYYY-MM-DD&type=news|deep|paper&item=<id>`，旧式无 `type` 链接仍按 news 兼容。新闻详情按「来龙 → 现状（摘要、长叙述、为什么重要）→ 走向 → 对我的意义」组织，缺失段落静默省略，之后再呈现证据概览、claims、来源和操作；深读呈现推荐理由、核心观点、关键点和适合读者；论文呈现阅读理由、研究结论、贡献、证据与局限。缺少新字段的历史数据按现有字段静默降级，有效个人会话下保留稍后读、收藏与新闻反馈操作；「更多资讯」同时提供原文与站内详情入口。RSS 继续读取 `watch` 字段并以「走向」标注。
- 浏览器通过不可由 JavaScript 读取的签名会话判断是否显示个人操作；普通访客看到的仍是纯阅读页。高权限后台口令不会持久化，也不会发送给日报接口。
- 反馈包括不感兴趣、更多类似、来源质量低、追踪/取消追踪。个人新闻卡直接展示不感兴趣与收藏，稍后读、更多类似、追踪和来源反馈收进原生溢出菜单；深读与论文直接展示收藏、把稍后读收进溢出菜单。日报、时间线、详情和收藏复用同一操作布局，来源质量低仍会在后续管线运行中按近 90 天反馈自然日机械降权，不修改 `sources.yaml`。
- 卡片上的稍后读、更多类似、追踪都是可撤销开关，再点一次即撤回对应记录；操作移入菜单不改变 API、localStorage 键或同步语义。
- ⭐ 收藏（仅个人会话）：独立于稍后读的永久精华库——稍后读是待读队列（读完沉底），收藏是"觉得最有价值就存"。精选、深度阅读、今日论文三类卡片上都有 ⭐ 按钮（再点取消）；收藏页按收藏时间倒序使用单列阅读流，并提供全部、新闻、深读、论文类型筛选。条目凭 `date + item_id` 引用从对应 daily 文件懒加载并重渲染完整卡片，跨天引用沿用 `日期:id` 复合键；服务端列表会并入本地高亮缓存（`news_fav`，永久不清理），换设备后卡片 ★ 状态一致。
- 追踪事件即使不进精选，也会出现在页面的追踪区；管线会用"更多资讯"补匹配，尽量防止断档。
- 深度阅读频道独立于新闻主管线，源来自 `sources.yaml` 的 `deep_sources`，每个源归入 `ai_engineering`、`tech_business`、`society_finance` 三栏（旧配置名 `zh_society_finance` 仍可读，新数据只写新名）。每天先从各栏选一篇过线文章，空栏名额再按总分释放，仍最多 3 篇且不降低 7 分门槛。`deep_sources.type` 可切换专用适配器；综合评论源可用 `topic_filter: finance` 仅保留宏观、商业、市场、劳动和公共经济政策文章。深读失败只丢当天深读推荐，不影响新闻日报产出。
- 今日论文频道同样独立于新闻主管线：抓 **Hugging Face Daily Papers**（社区精选 + 点赞，公开接口无需 key），LLM 按 `interest_profile.md` 的学习坐标（前端/全栈/AI 应用/自动化）从当天几十篇里挑 3-4 篇，产出中文标题、"该读什么/该补什么概念"，带点赞数与"是否有开源代码"标记。写进 daily js 的 `papers` 字段，前端日视图「今日论文」板块渲染（紫色左边框区别于深读）。论文不是新闻——不进精选评分、不占五类名额。参数在 `config.yaml` 的 `papers` 段（`enabled`/`lookback_days`/`max_candidates`/`pick_threshold`/`pick_max`/`seen_keep_days`），失败只记日志、不阻断每日产出。
- 舆论观察：微博/B站热榜（`sources.yaml` 的 `pulse_sources`，直连公开接口）只作两个用途，热榜词条本身永不成为新闻条目——①`opinion_pulse` 用 LLM 挑 2-3 个值得说的传播现象，讲"为何热/群体情绪/平台机制"（滤纯明星八卦），写 daily js 的 `opinion` 字段，前端「舆论观察」板块渲染（琥珀色左边框）；②co-occurrence 暗排序：热榜词条与真新闻事件文本重合（4 字连片或二元组覆盖 ≥0.5）时，该事件最终分乘 `opinion.cooccur_bonus`（默认 1.08）。参数在 `config.yaml` 的 `opinion` 段；热榜抓取或 LLM 失败只丢当天舆论板块，不阻断日报。
- 周综述按周一至周日的自然周生成：主管线每次日报运行都会幂等检查最近一个已结束周，覆盖至少 **5/7** 天且报告尚不存在时才合成，低于门槛则跳过；报告会列出覆盖期数与缺失日期。新版静态数据为兼容型 v2，包含周主线、数字盘点、3-6 个动态主题、代表报道复合引用（`date:item_id`）、上周判断回收、下周信号，以及单列的深读/论文引用；写入前会校验全部引用存在。旧周报不改写，低于 5/7 的旧报告不进入新版归档。**失败只记日志、不阻断每日产出，也不进发布校验**；不新增 workflow。

### 验证与移除

- 管线回归：`python news-pipeline/tests/test_pipeline.py`。该测试不调 LLM、不联网；改评分、聚类、可信度审计、健康度、事件登记、偏好学习、深读、周综述、RSS 或搜索索引逻辑后必跑。
- 客观性回归：`python news-pipeline/tests/test_objectivity_audit.py`（证据合同、审计/修复/降级、夹具完整性）与 `python news-pipeline/tests/test_shadow_rollout.py`（shadow 快照隔离与环境还原）。两者同样不调 LLM、不联网，静默通过、失败非零退出；改客观性审计、证据结构或 shadow 流程后必跑。
- 新闻页回归：`npm run test:news`。测试使用 Node 内置测试器与 jsdom，覆盖新旧路由、DOM 渲染、个人操作 API 合同、无障碍状态和空数据降级；修改 `source/news/index.html`、`source/news/news.css` 或 `source/news/js/` 后必跑。
- 完整交付前运行 `npm run build`，确认 Hexo 能把新闻页 ES Modules、样式、字体和静态数据原样输出到 `_config.yml` 指定的 `dist/news/`，并确认 `dist/admin/` 仍存在。
- 移除方式：删除 `source/news/`、`news-pipeline/`、`.github/workflows/daily-news.yml`、`_config.yml` 中的 `- news/**`、`_config.fluid.yml` 菜单中的 `news` 项即可完全剥离。
- 历史沿革：管线原为独立项目 `D:\每日新闻网站`，已在 2026-07-04 迁入本仓库并退役。
