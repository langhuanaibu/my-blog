# Aoitsuki Blog

这是 Aoitsuki 的个人博客项目，当前采用 `Hexo + Fluid + Vercel` 的静态博客架构。

## 当前架构

- 博客框架：Hexo
- 主题：Fluid
- 内容源：`source/_posts/*.md`
- 静态资源：`source/images/`
- 自定义脚本：`source/js/`
- 构建输出：`dist/`
- 部署平台：Vercel
- 评论系统：Twikoo
- 站点域名：`https://aoiblog.top`

## 目录说明

```text
source/_posts/          文章 Markdown
source/images/          图片资源
source/js/              自定义前端脚本
source/about/           关于页面
source/friends/         友情链接页面
source/guestbook/       留言板页面
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

- 新文章写入 `source/_posts/`。
- 图片统一放入 `source/images/`，文章中使用 `/images/<filename>`。
- 文章 URL 使用 `/:year/:month/:day/:title/`。
- 迁移自旧站的文章保留 `old_id` 和 `twikooPath` front matter，用于旧链接兼容和 Twikoo 评论路径。

## 迁移说明

本项目曾使用 `Astro + Vercel Serverless API + MongoDB + public/admin.html` 架构。

2026-06-18 起迁移为 Hexo 静态博客：

- 线上公开 API 返回的 19 篇文章已迁移为 Markdown。
- 后台草稿未迁移。
- 旧 `/articles.html#article_id` 链接由 `source/articles.html` 兼容跳转到新文章地址。
- Twikoo 评论使用每篇文章的旧 `article_id` 作为 path，尽量保留旧评论关联。
- 旧 Astro 前台、Vercel API 和静态后台不再作为运行入口保留。

详细决策见 `docs/archive/2026-06-18-hexo-fluid-migration.md`。
