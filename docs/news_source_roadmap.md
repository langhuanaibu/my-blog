# 日报信源待办

> 日报信源扩展的活跃待办清单。信源终局定案写在 `news-pipeline/sources.yaml` 尾部注释，现行机制写在 `readme.md` 日报章节；本文件只记**还没做完的事**，全部完成后删除。
>
> 最后更新：2026-07-18

## 📅 客观性 shadow 验收（待完成）

2026-07-18 公开路径落地的是 **interim wording hotfix**，不是已验收的完整证据系统。
`--objectivity-shadow` 的 7-day 指标门和 45-case / three-run 夹具门都通过前，
**active mode is not enabled**，**live acceptance has not occurred**。详细阈值与安全边界见
`docs/news_objectivity_plan.md`。

- 每天保存 GitHub step summary 中的运行时间、全文/混合/摘要分布、抓取重试、
  修复/降级、独立链分布，以及同口径的 `selected_before_audit`、
  `selected_after_audit`、`audited_candidate_count`、`demoted_from_selected` 和
  `source_reference_concentration`（按入审前精选的来源引用次数计算）。
- 达标后只是获得 active 人工评审资格，不自动切换配置。

## 中文视角对冲源评估（待客观性验收后判）

实证（07-11~17 精选）：涉华条目单源率 56%，其中单源=西方外媒 ≈1.3 条/天，集中在大陆媒体不报的敏感议题（仅存单一西方叙事）。评估补一个中文国际视角源做涉华事件交叉：

- 候选路径：联合早报官网 RSS 已 404 判死（sources.yaml 尾注），重议只能走自建 RSSHub 的 zaobao 路由（如 `/zaobao/znews/china`），先浏览器验证路由可达再谈。
- 论证门槛：必须正面回应尾注"world 41% 过剩、任何 world 向新源默认拒"的定案——论据是"补涉华第二叙事"而非"加 world 产能"，可考虑低 credibility + mixed 类目接入以控制增量。
- 若路由不可达或增噪明显，明确记"不加"并销账。

硬门：在增加任何主管线信源前，先收集至少 **14-day source metrics before adding sources**，
包括抓取成功/零更新、候选量、入选量、单源高风险率、独立证据链和集中度。
这 14 天只观测现有源，不回填历史、不同时加源；数据与人工审查都支持后才能重议。

## 📅 2026-07-22：#7 第一轮单变量调参

样本固定为 2026-07-15 至 2026-07-21。本轮只判断 `pick_max: 24` 是否截断仍值得读的内容，不同时修改 `pick_threshold`、`interest_weights`、`fit_span` 或兴趣画像。

- 统计 7 天中触及 24 条上限的天数。
- 对每个触顶日抽查排名 25–28 的事件，记录是否仍应进精选。
- 若至少 3 天触顶，且抽查事件中至少三分之二值得进精选，则只把 `pick_max` 从 24 调到 28；否则保持 24。
- 调整后再观察至少 7 天。第二轮才分析各类「过线候选量 → 入选量」，区分供给不足与权重问题。
- `quality-health.json` 只用于审查聚类拆分、字段删除和降级，不作为类别调权依据。画像参数只根据反馈、收藏、稍后读和人工阅读体验调整。

---

以下扩源只优化独立深读的阅读结构，不直接解释或修复主管线财经精选占比。每次只启用一个新源，通过数据门和人工门后再进下一阶段。

**统一验收口径**：

- 数据门：标题、URL、时间和摘要/正文指标可解析，无连续 3 次抓取失败，并有足够历史或线上样本完成评分。
- 人工门：抽查至少 3 篇，确认有独特阅读价值、主题符合栏目，不是现有源或 AIHOT 的重复替代。
- 不以「未入选」单独判定源失效；结合 `deep_health.json` 的抓取、去重候选、主题匹配、过线和入选统计复核。

## #10 阶段一：阮一峰《科技爱好者周刊》

已启用 `https://www.ruanyifeng.com/blog/atom.xml`，进 `tech_business` 栏。该 feed 已验证可取到周刊正文。

- 观察期：14 天（至 2026-07-31）。
- 通过统一验收后保留，并进入 #9；未通过则 `enabled: false` 并记录原因。

## #9 阶段二：晚点 LatePost

专用适配器已实现，信源保持禁用，待 #10 验收后再单独开启。

- 固定使用 `https://www.latepost.com`，调用公开 `POST /news/get-news-data`，只取 `programa=4` 长报道。
- 适配器已处理「昨天」、「MM月DD日」和完整年月日；无法可靠定年份时丢弃。详情页只用于补摘要与正文长度。
- 启用后观察 14 天，通过统一验收后保留。

## #8 阶段三：英文财经深读

四个候选均已写入 `deep_sources` 但保持禁用，待 #9 验收后按以下顺序单源开启：

1. Noahpinion：`https://noahpinion.substack.com/feed`，观察 7 天。
2. Marginal Revolution：`https://marginalrevolution.com/feed`，观察 7 天，重点复核短文和 AI 主题偏移。
3. Apricitas Economics：`https://www.apricitas.io/feed`，低频源。
4. Kyla's Newsletter：`https://kyla.substack.com/feed`，低频源。

四源均进 `society_finance` 栏并启用 `topic_filter: finance`；只允许宏观、商业/产业、市场、劳动就业和公共经济政策文章进入候选。Apricitas 与 Kyla 的历史文章只做资格审查，不发布到「今日深读」；生产继续使用 78 小时窗口。

Money Stuff 与 FT Alphaville 均不再探测：前者无官方 RSS，不接受第三方镜像的稳定性与维护风险；后者已确认存在 Actions 出口封锁。
