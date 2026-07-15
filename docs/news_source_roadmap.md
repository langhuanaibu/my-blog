# 日报信源待办与验收记录

> 日报信源扩展的活跃待办清单。信源终局定案（判死清单、各轮结论）写在 `news-pipeline/sources.yaml` 尾部注释，机制说明在 `readme.md` 日报章节——本文件只记**还没做完的事**，做完即删对应条目，全部完成后删除本文件。
>
> 最后更新：2026-07-12

## ✅ 已销账

- **07-11 CI 首跑验证**（2026-07-12 核实）：opinion（舆论观察）字段 07-11/07-12 连续两天正常产出，微博 + B站条目均在，Actions 美国出口 IP 可达；LLM `deepseek-v4-flash` 正常出分（日报两天正常生成、精选非空校验通过）。

## 📅 2026-07-14：六个新源验收

按 `source/news/data/source_health.json` 决定 ftcn / anthropic / anthropic-eng / cls-depth / yicai / ithome 去留。失败处置口径各自写在 `news-pipeline/sources.yaml` 对应注释（如 ftcn 仍败则 `enabled:false` 收口）。

前两天（07-11/07-12）初步信号：

| 源 | 状态 | 备注 |
| --- | --- | --- |
| ithome | ✓ 稳定 18 条/天 | 基本稳过 |
| cls-depth | ✓ 稳定 18 条/天 | 基本稳过 |
| ftcn | ✗ 连续 error | 走 RSSHub 中转后仍失败，大概率收口 |
| yicai | ⚠ 两天 0 条且无报错 | 接口通但抓不到内容，验收前查适配器解析 |
| anthropic | 0 条无报错 | 官方博客低频，可能正常 |
| anthropic-eng | ⚠ health 里根本没出现 | 连记录都没有，验收前查配置是否生效 |

验收前值得提前处理的疑点：yicai 适配器解析、anthropic-eng 为何未进 health 记录。

## 📅 约 2026-07-17：#7 榨信号

新源跑满一周后，用 source_health + 精选构成调阈值/权重/画像参数。

- **36氪去留同场判**：120 条抓取 → ≤3 条精选，全场性价比最差，目前缓刑中。
