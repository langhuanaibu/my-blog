# 客观性夹具允许多个正解

45 条客观性夹具的九个风险标签并不互斥：它们混合了「主张类型」（`armed_conflict`、`company_claim`、`legal_procedure`…）和「证据缺陷」（`sensitive_single_source`、`shared_evidence`、`forbidden_fabricated_balance`）两条正交轴，一条证据完全可以同时命中两者。因此每条夹具用 `expected.accepted_labels` 列出所有据文站得住的标签，Judge 仍只选一个，命中集合即算一致。

这不是放水。2026-07-25 的诊断轮 Run #30157820536 显示，19 次标签错配中有 17 次落在四条固定接缝上（`armed_conflict→sensitive_single_source` 六次、`waic_framing→company_claim` 五次、`shared_evidence→company_claim` 三次、`forbidden_fabricated_balance→company_claim` 三次），而且好几条上 Judge 的答案比夹具更有据——`waic-05` 的 "a lab handout called its robot fully autonomous" 正命中 `company_claim` 类别描述原文的 "readiness claims"，三轮判法完全一致。武断的是「单一正确答案」这个设定本身，不是 Judge。`company_claim` 单独吸走十一次，因为它按「谁在说」定义，其余类别按「什么风险」定义。

曾考虑给词表加 `none`，让面对干净证据的 Judge 有合法答案，**这个方案被否决**。三轮里全部八次结构无效都落在七条夹具上，它们的共性不是「无风险」而是**缺席型风险**：原文本身干净，风险在于写作者可能添加——`conflict-05` 写的是 "temporary pause" 且双方时间一致、`company-04` 同比基准完整、`shared-05` 是真正独立的证据链。这七条**每条都有种下的红线**，接受 `none` 等于让 Judge 漏掉种下的风险却记一次命中，并会使 `forbidden_fabricated_balance`（全五条都是缺席型）整类失去测试价值。改为在 Judge prompt 里说明「严谨的证据同样携带风险，必须标注，不得回答无风险」，八次结构无效一次性归零。用真实 Judge 答案回放验证过两种方案：只拆指标不改 prompt，最差轮结构 91.11%、不通过；加上 prompt 修正才是 100%。

另外两个备选也被否决：按两条正交轴重设标签体系最正，但 `waic_framing↔company_claim` 这类同轴接缝仍在，且要重写 prompt、校验、夹具与评分；在 prompt 里写死接缝裁决规则则同样武断，还依赖模型记住裁决表，换模型即复发。

配套纪律：**接受集每扩一条都必须引 `CATEGORY_DESCRIPTIONS` 原文完成论证并留档，不得因为想让某轮通过而事后加入。** 接受集与阈值同属验收口径，变更需人工批准，不得由自动流程改动。已按此拒绝过 `conflict-04`——它三轮全部被判 `sensitive_single_source`、论证也站得住，但当轮门已通过，此刻扩集的唯一动机是拉高余量。
