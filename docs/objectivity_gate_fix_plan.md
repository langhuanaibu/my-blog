# 客观性 45 条夹具门修法提案

> 状态：**待执行提案**。本文件不是现行规范——现行验收口径仍以 `docs/news_objectivity_plan.md` 为准。
> 执行完成后按 CLAUDE.md 文档纪律：现行事实并入 `news_objectivity_plan.md` 与根目录 `CONTEXT.md`，删除本文件。
> 定案依据：2026-07-25 grilling 六项决策 + run 30157820536 逐条实锤（见 Issue #15 评论）。

## 一、背景与实锤

45 条夹具门已连续三次未通过（07-22 run 29894388908、07-25 run 30156885233、07-25 诊断轮 run 30157820536）。PR #38 给 `score_run` 加了逐条 `case_findings` 后，诊断轮把失败完全定位到**测量层**：

| 轮次 | redline_count | 其中标签错配 | 其中残留违规 | 结构 | 归因 |
|---|---|---|---|---|---|
| 1 | 10 | 10 | **0** | 93.33% | 100% |
| 2 | 6 | 6 | **0** | 91.11% | 90.32% |
| 3 | 3 | 3 | **0** | 97.78% | 100% |

四个实锤结论：

1. **管线安全行为干净**：三轮 `reported_redline_count` 全为 0，没有任何候选把违规内容留在最终产出。`redline_count` 的 10/6/3 百分之百来自标签错配。门显示「红线 10」，按规范与 Judge prompt 对红线的定义（残留于最终候选的违规），真实红线是 0。
2. **错配高度系统化**：19 次错配里 17 次落在 4 条固定接缝——`armed_conflict→sensitive_single_source` ×6、`waic_framing→company_claim` ×5、`shared_evidence→company_claim` ×3、`forbidden_fabricated_balance→company_claim` ×3。`company_claim` 单独吸走 11 次：它按「谁在说」定义，其余类别按「什么风险」定义，一条公司自吹必然同时满足两者。且多条上 Judge 的答案本身站得住（`waic-05` "fully autonomous" 命中 `company_claim` 类别描述原文 "readiness claims"，三轮判法完全一致）。
3. **无风险条目无法合法作答**：`company-04`（营收 80M←72M，自带同比基准、无可指摘风险）三轮两轮结构无效——词表强制非空标签，Judge 面对干净条目交不出风险标签。
4. **归因指标被结构失败污染**：`score_run` 中 `attribution_total` 在有效性检查之前自增，结构无效条目自动记为归因失败。第 2 轮归因 90.32% 与归因本身无关：4 条结构无效中 3 条 `attribution_required: true`，31−3=28 → 0.9032，分毫不差。

问题不是 Judge 认不准，也不是管线不安全，而是：**两个正交概念（安全违规 / 分类分歧）被压进同一个计数器，且单一正确答案的设定本身武断。**

## 二、术语定案

执行时把下列术语并入根目录 `CONTEXT.md`（目前术语表零客观性词汇，正是两概念被合并进同一计数器而长期无人察觉的原因）：

- **红线**：最终产出（候选）中残留的客观性违规。只有它才是安全事故。_Avoid_：标签错配、复合计数。
- **风险标签**：Judge 对证据风险类型的分类判断（9 类词表 + `none`）。分类分歧不是红线。
- **接受集**：一条夹具所有站得住的风险标签集合。承认题目可以有多个正解，不是改错题迁就答案。
- **标签一致性**：Judge 命中接受集的比率。它测的是 **Judge 校准度**，不是管线质量。
- **结构合法**：Judge 批次输出符合 schema 且逐条可计分。结构失败只扣结构门，不得污染其他指标。

## 三、四门新口径

仍三轮取最差，`accepted` = 四门全过：

| 门 | 口径 | 阈值 | 变化 |
|---|---|---|---|
| 残留红线 | `reported_redline_count`（仅候选中残留的违规） | 最差轮 = 0 | 从复合计数中剥离，阈值不变 |
| 标签一致性 | 命中接受集的条目 / **结构有效**条目 | 最差轮 ≥ 90% | **新门**（原先混在红线里） |
| 归因准确率 | 归因正确 / **结构有效**且 `attribution_required` 的条目 | 最差轮 ≥ 95% | 分母解耦，阈值不变 |
| 结构合法率 | 有效条目 / 45 | 最差轮 = 100% | 完全不变 |

原则：每个指标只测自己的东西。结构无效由结构门（100%）独立兜底，不再让同一次失败在多个指标上重复扣分。0/95%/100% 三个既有阈值全部不放宽；90% 是新增的门，不是任何门的替代。

## 四、接受集逐条清单（初稿，执行 PR 逐条评审）

有实锤支撑、且能引类别描述原文论证的条目：

| 夹具 | 接受集 | 论证 | 实锤 |
|---|---|---|---|
| `conflict-01` `conflict-02` `conflict-03` | `{armed_conflict, sensitive_single_source}` | 单方军方说法 + 无独立核实，两义同时成立 | 6 次错配，方向一致 |
| `waic-03` `waic-05` | `{waic_framing, company_claim}` | 命中 `company_claim` 描述原文 "readiness / benchmark claims"；`waic-05` 三轮全判 `company_claim`，判法稳定 | 5 次 |
| `shared-02` | `{shared_evidence, company_claim}` | "figures from one company release" 两义皆据文可立 | 3 次 |
| `balance-02` `balance-04` | `{forbidden_fabricated_balance, company_claim}` | "Only the company's statement is available" | 3 次 |
| `company-04` | `{company_claim, none}` | 自带同比基准，无适用风险；作为**误报校准项**保留 | 2 次结构无效 |

**明确不进接受集**（属 Judge 真错，由 90% 门容纳）：

- `causal-04 → waic_framing`（1 次）：关税后安排会谈与会展营销无关，论证不成立。
- `shared-05 → legal_procedure`（1 次）：court docket 在场但条目语义是「两条独立证据链成立」，牵强。`shared-05` 是否加 `none`（负例语义：合法 corroboration）留待执行 PR 评审，不在本初稿预设。

**防滑坡纪律**：

1. 接受集每扩一条，必须引用 `CATEGORY_DESCRIPTIONS` 原文完成论证并记录在执行 PR。
2. 禁止「跑一轮、把错的加进接受集」的事后扩集——扩集只能来自语义论证，不能来自想让某轮通过。
3. 接受集与阈值一样属于验收口径，变更须人工批准，不得由自动流程改动。

## 五、执行时的代码改动清单（本提案不做）

全部集中在 `news-pipeline/`，注明：`objectivity_eval.py` **不在运行时指纹内**（`runtime_paths = [daily_news.py, rollout_validation.py]`，见 daily_news.py `emit_rollout_evidence`），执行合并**不会**重置每日五门台账时钟，合并时机无约束。

- `objectivity_eval.py`
  - `score_run`（现 :268）：一致性判定改为 `labels ⊆ accepted_labels`；红线 = 仅 `reported_redline_count`；归因与标签一致性分母均改为结构有效条目；`case_findings` 保留并在 `label_mismatch` 条目中带上接受集。
  - `acceptance_result`（现 :349）：`worst` 增加 `label_agreement`；`accepted` 判定四门。
  - `JUDGE_SYSTEM`（现 :90）：允许 `none` 作答（"若无任何列出风险适用，labels 为 [\"none\"]"），其余不动。
  - `_validated_judge_batch`（现 :233）：`none` 合法且只能单独出现。
  - `validate_fixture_schema`（现 :140）：校验 `expected.accepted_labels ⊇ {category}`（或含 `none`）、仍强制 9×5、唯一 ID、词表闭包。
- `fixtures/objectivity_evidence.json`：按第四节清单加 `accepted_labels`；重算并更新 `CORPUS_SHA256`（现 :19）。语料 excerpt 与 expected.redlines 文档字段不动。
- `tests/test_shadow_rollout.py`：更新计分用例；新增 `none` 作答、接受集命中/未命中、归因分母解耦三组用例。
- 文档同步：`news_objectivity_plan.md` 45-case 门段落改为四门新口径；`CONTEXT.md` 并入第二节术语；完成后删除本文件。

## 六、验证步骤

1. 本地 `python -m pytest news-pipeline/tests/` 全绿（当前基线 311 项）+ `npm run test:news`。
2. 合并后手动触发 `Objectivity Acceptance` 真跑三轮。
3. 用 `case_findings` 核对：四条接缝错配归零；剩余分歧均为真分歧且在 90% 门内；`company-04` 不再出现 `invalid_structure`；归因不再随结构波动。
4. 结果（通过与否都）记回 Issue #15。若通过，45 条夹具门关闭，`objectivity.mode` **仍保持 `interim`**——夹具门只授予 active 人工评审资格，7 日 shadow 门与人工评审独立在前。

## 七、边界

- 不动每日五门台账（Issue #15 的 selection/trajectory/enrich/objectivity_shadow/source_metrics），与 07-26 起算的线上观察互不影响。
- 不改 `pick_dynamic`、不加信源、不处理 #20 与 #29–#35。
- 提案本身不改任何代码与夹具；未获批准前，本文件对任何自动流程无约束力。
