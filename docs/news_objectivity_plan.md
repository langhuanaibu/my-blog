# 日报客观性改写计划（2026-07-18）

> 本文件是一次性改造计划与验收记录。验收完成后按"文档收口"规则：事实并入 `readme.md` 日报章节，本文件删除。
>
> 动因：详情页 `detail` 长文会原样继承来源媒体的立场措辞。实例（2026-07-18）：习近平首现 WAIC 一条仅有 BBC 中文单一来源，BBC 的定性框架（"应对美国技术封锁"等）被当作事实陈述写进正文。

## 当前发布状态

- 公开日报当前只启用 **interim wording hotfix**：`objectivity.mode: interim`
  保留生成 prompt 的归因/去偏规则和原有 support-only 事实支撑审计。
- 完整正文证据、独立证据链、客观性定向修复/降级/降档只在
  `--objectivity-shadow` 或未来 `objectivity.mode: active` 运行。**active mode is not enabled**；
  **live acceptance has not occurred**，也没有完成 7 天线上验收。
- shadow 命令为 `python news-pipeline/daily_news.py --objectivity-shadow`。GitHub Actions
  的 `shadow` job 在 `generate` 成功后 checkout 最新 `main`，限时 24 分钟、只读仓库、
  允许失败；它不 commit/push，也不改变已提交的 interim 公开数据。CLI 会先把当前
  `DATA_DIR` 递归复制到可清理的临时目录，feedback/profile/registry/weekly 等读取与后续
  写入都在快照中进行；正常返回、提前返回、异常和校验失败均会清理快照并恢复环境。
- 手动 `Objectivity Acceptance` workflow 只允许从 `main` 触发，复用 `LLM_API_KEY` 连跑三轮固定夹具，只上传
  聚合报告，不提交数据。批次结构稳定性修复（非法批次递归拆小、单条重试一次，每轮最多
  调用 Judge 60 次，预算耗尽保守记为结构失败）已随 PR #36 落地并生效：结构合法率从
  22.22% 升到 91%–98%，归因从 29.03% 升到 96.77%–100%。
- 2026-07-25 诊断轮 Run #30157820536 把剩余失败**全部定位到测量层**：三轮残留违规均为 0
  （管线安全行为干净），19 次标签错配中 17 次落在 4 条固定接缝，8 次结构无效全部落在
  缺席型风险夹具上。据此完成上文的四门拆分、接受集与 prompt 修正。`active` 继续禁用；
  实时状态与每日计数以 GitHub Issue #15 为准。

### 证据合同与页面

完整路径的条目可带 `evidence: {basis, publisher_count,
independent_chain_count, degraded}`；`basis` 仅为 `fulltext|mixed|snippet`。来源可带
`evidence_basis` 和可核验的 `evidence_chain`，claims 继续用
`{text, kind, sources}` 展示类型和归因来源。前端只在整个结构合同有效时显示
证据概览；旧数据或异常结构静默兼容。`degraded: true` 表示仅摘要或修复失败后
的保守降级；高风险事件若复审仍失败，从精选降至更多资讯。

正文只是当次运行内存中最多 4,000 字的短暂证据；**full text is not persisted**
到 daily/weekly/feed/search/registry/profile/health/vocab 或任何公开数据。抓取只读公开静态
HTML，不执行脚本、不登录、不迁回私网，不做 **paywall** bypass；无法合法获取时
退化为 RSS snippet。

## 一、已落地：interim 生成层客观性规范（2026-07-18）

改动仅在 prompt 层（`news-pipeline/daily_news.py`），零新字段、零前端改动、零新增 LLM 调用：

- **ENRICH_SYSTEM**（精选深加工，产出 title/summary/why/context/detail）追加"客观性规范"块：
  - 总纲：只陈述可追溯的事实，主张归属于提出者，争议和不确定性显式保留。
  - 归因：媒体的定性判断/推断/立场性表述必须显式归因（"X 报道称"），不得写成事实；指控写"X 指控"。
  - 跨源印证：多源事件优先写各源共同证实的事实；单源支撑的立场性内容必须归因到该源。
  - 去偏见 checklist：剥离情绪化形容词、未归属价值判断、无依据动机推断（"意在/旨在/企图"）、相关性写成因果、缺基准数字的程度渲染。
  - 禁止为"平衡"编造原始报道中不存在的对立观点；宁缺毋造。
  - 立场性判断优先入 claims（kind=analysis）而非正文叙述语气。
- **detail 字段定义**（`enrich()` 内模板）补归因要求，在主要出问题的字段处再钉一次。
- **BRIEF_SYSTEM**（今日主线）补一行措辞中性规则。

### 设计决策（grill-me 两轮定案，防重议）

1. **只做改写层，不做评级层**：不加 objectivity/stance 字段。claims 三分（fact/analysis/uncertain）+ status「有争议」已承担标注职责；正文措辞才是问题本体。
2. **剥离 + 归因，不是全删**：外媒如何定性一件事本身是信号；归因后从"事实陈述"降级为"某方观点"，信息量不损。
3. **公开路径暂不加完整审计 pass**：该历史决定现由 shadow rollout 取代。
   完整审计代码已存在，但在验收前不得进入公开数据。
4. **评分层不动**：BBC 中文维持 credibility 9 / T1 / fact。选题没错、措辞有错，用选题层的刀解文字层的问题会误伤正常国际新闻。
5. **外部调研取舍**（journalism skills / fact-check-skill / NeuS 等）：只吸收总纲句、机械 checklist、跨源印证三样进 prompt。不采纳：联网核查一手资料（架构级改动，与离线批处理管线和自用成本冲突）、七态内容分类与证据账本（claims + status + source_indexes 已覆盖）、七段固定输出结构（前端重构，违背通读取向）。理论留档：选材偏见比措辞偏见更隐蔽（BASIL）→ 文字层改写与源层对冲缺一不可；改写可能引入新信息/新偏见（NeuS）→ "禁止编造"规则与既有 support audit 是必要兜底。

## 二、验收门槛（尚未达成）

- **7-day gate**：连续 7 天观察 shadow 任务成功率、红线、降级/降档、单源高风险和
  来源集中度，并通读 detail/summary 的归因、情绪词和虚构平衡。机器指标使用同口径字段：
  `selected_before_audit`、`selected_after_audit`、`audited_candidate_count`、
  `demoted_from_selected` 和按来源引用次数计算的 `source_reference_concentration`。
- **45-case corpus / three-run gate**：固定 45 条合成短夹具（9 类各 5 条）每次用指定模型连续跑
  3 次；取最差一轮判**四门**，四门全过才 `accepted`。夹具覆盖 WAIC 框架、法律程序/指控、
  武装冲突、公司主张、无基准数字、动机/因果推断、敏感单源、转载共享证据链和禁止虚构平衡。

  | 门 | 口径 | 阈值 |
  |---|---|---|
  | 残留红线 | 最终候选中残留的违规条数 | = 0 |
  | 标签一致性 | 命中接受集的条目 / 结构有效条目 | >= 90% |
  | 归因准确率 | 归因正确 / 结构有效且需归因的条目 | >= 95% |
  | 结构合法率 | 结构有效条目 / 45 | = 100% |

  **每个指标只测自己的东西**：结构失败只扣结构门，不再连带把归因和标签算作失败
  （2026-07-25 诊断轮的归因 90.32% 曾完全是结构污染的假象）；标签分歧是 **Judge 校准**
  信号，不再计入红线（同一轮 `redline_count` 10 而真实残留违规为 0）。
- **接受集**：9 个标签并非互斥——它们混合了「主张类型」（armed_conflict、company_claim…）
  与「证据缺陷」（sensitive_single_source、shared_evidence…）两条正交轴，单一正确答案
  的设定本身武断。因此每条夹具用 `expected.accepted_labels` 列出所有据文站得住的标签，
  Judge 仍只选一个，命中集合即算一致。**扩集必须引 `CATEGORY_DESCRIPTIONS` 原文论证**，
  不得因为想让某轮通过而事后加入；接受集与阈值同属验收口径，变更需人工批准。
  当前 8 条接缝夹具已扩集：`conflict-01/02/03`（+sensitive_single_source）、
  `waic-03/05`、`shared-02`、`balance-02/04`（+company_claim）。
- **缺席型风险**：约 7 条夹具的风险不在原文里，而是「写作者可能添加」的风险
  （temporary pause 被写成永久和平、基准完整的数字被外推、真独立证据链被合并、
  单方材料被补上虚构回应）。Judge prompt 明确要求标注这类风险，不得回答「无风险」——
  2026-07-25 诊断轮全部 8 次结构无效均由此产生，且全部落在这 7 条上。
- 语料固定为 checked-in 文件及其 SHA-256；schema 强制恰好 45 条、9 类各 5 条、唯一 ID、
  label/redline 词表、`accepted_labels` 必须包含 `category`。证据先走生产 `enrich` 和完整
  audit/repair/fallback，独立 judge 仅接收证据与最终候选；category、expected 元数据和
  0/90%/95%/100% 阈值不进入候选生成或 judge 输入，候选自报 redline 不受信任。
  验收报告含逐条 `case_findings`（失败条目 id、接受集与 Judge 实际作答），供排查。
- 两道门都达标且人工核验后，才能另行评审是否将 `mode` 改为 `active`。
  本文档不表示任何线上验收已完成。

## 三、源层配套：涉华单源率实证(2026-07-18 统计)

改写只能在单一来源的事实框架内中性化——选材偏见需要源层对冲。统计 07-11~07-17 七天精选：

- 精选 144 条，涉华 25 条（17.4%）；**涉华单源率 56%**（14/25），超过预设 50% 阈值。
- 其中单源且来自西方外媒 9 条（纽时中文 4、BBC 中文 3、BBC World 1、NPR 1），≈1.3 条/天。
- BBC 中文的单源条目集中在大陆媒体不报的敏感议题（政治局委员被双开、异见人士出逃等）——此类条目**只有单一西方叙事**，是对冲源唯一能补的视角缺口。

→ 结论：达到评估线。已在 `docs/news_source_roadmap.md` 立"中文视角对冲源评估"待办（联合早报官网 RSS 已 404 判死，重议路径为自建 RSSHub 的 zaobao 路由；须先过 world 41% 过剩这道尾注定案的论证）。

## 四、源验收与榨信号状态（本计划启动时已完成，仅索引）

- 六源验收（07-16 完成）：ftcn / yicai 停用，anthropic / anthropic-eng / cls-depth / ithome 保留，记录在 `sources.yaml` 各源注释。
- 榨信号第五轮（07-17 完成）：36氪撤销缓刑保留；精选构成 world 41% / finance 10.7%；定案见 `sources.yaml` 尾注。原单变量调参已由 `docs/news_selection_plan.md` 的动态阈值与类目保留席改革取代，部署后的观察事项继续由 `docs/news_source_roadmap.md` 记录。
