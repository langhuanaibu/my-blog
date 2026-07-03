# 项目全局约束 (CLAUDE.md)

本文件为项目最高约束。任何操作前必须阅读。**先定规则，再改动；先守边界，再优化；先验证，再交工。**

## 1. 架构定位与修改边界
- **当前架构**：Hexo + Fluid 静态博客，部署于 Vercel，内容源为 `source/_posts/*.md`。
- **API 层**：`api/` 下的 Vercel Serverless 接口仍保留，用于在线后台的发布和设置功能。
- **核心原则**：渐进式迭代，保持线上稳定。
- **严格边界**：仅在要求的特定作用域内修改。禁止擅自重构接口、大改后台逻辑、修改已有文章内容。
- 旧 Astro 前台、Vercel API 和静态后台（`public/admin.html`）不再作为运行入口。历史记录见 `docs/archive/`。

## 2. 目录与命名规范
根目录严禁堆放临时文件，仅限全局配置和规范文档（如 `readme.md`, `memory.md`, `skill.md`）。
每次改动完成前，必须清理为调试、测试或预览临时创建的文件、目录和临时代码，不得把测试或临时内容留在工作区。
- **`source/_posts/`**：文章 Markdown 文件，文件名格式 `YYYY-MM-DD-slug.md`。
- **`source/images/`**：图片资源，含 `covers/` 子目录。
- **`source/js/` & `source/css/`**：自定义前端脚本和样式。
- **`source/admin/`**：在线后台页面 `index.html`。
- **`source/about/`, `source/friends/`, `source/guestbook/`**：独立页面的 Markdown 源文件。
- **`api/` (Vercel接口)**：纯业务接口，一文件一职责，小驼峰命名（如 `adminArticles.js`）。
- **`tools/`**：迁移和维护工具脚本。
- **`news-pipeline/`**：每日新闻日报生成管线（Python），由 GitHub Actions 每日运行，数据写入 `source/news/data/`。本目录是唯一真源（原 `D:\每日新闻网站` 已退役）。
- **`docs/archive/`**：存放历史重构文档归档。

## 3. 交互设计与工作流
- **体验至上**：为目标设计，系统承担复杂性（能推断不让用户填），反馈要引导下一步。
- **沟通方式**：默认中文，代码/命令英文。结论先行，不铺垫不拍马屁。直接给最合理方案，勿频繁确认。
- **安全底线**：密钥/Token绝不进代码。遇到报错必须排查根本原因，严禁为了跑通而注释报错。

## 4. 验证与提交流程
- **改完必验**：修改后必须执行 `npm run build` 或 `npm run dev`，确保页面正常、`/admin/` 兼容、API连通。无验证不交工。
- **清理收尾**：验证结束后必须检查工作区，确认没有遗留测试文件、临时文件或临时调试代码。
- **文档同步**：架构变动、运行方式变动或有复用价值的踩坑经验，必须更新至 `readme.md`。
- **Git操作**：Commit message 用简明英文。**严禁自动 `git push`**（仅用于跨设备同步，需等待用户明确指令）。
  - **唯一例外**：GitHub Actions 的 `daily-news.yml` 每日自动 commit + push，且仅限 `source/news/data/` 路径。管线脚本内置数据校验（精选非空、文件完整），校验失败即中止、不提交。此例外经用户明确批准（2026-07-04），不得扩大到其他路径。
