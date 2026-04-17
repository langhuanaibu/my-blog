# 博客 Astro 渐进式迁移架构设计 (Spec)

## 1. 架构概述
本次迁移的目标是将现有博客前端（原生 HTML/JS/CSS）渐进式迁移至 **Astro**，以提升前端开发体验和页面加载性能。
核心原则为 **“前台重构，后台与 API 冻结”**：
- **前端**：使用 Astro 替代原有的 `index.html` 和 `articles.html`。
- **后端**：保留 Vercel Serverless Functions (`/api/*.js`) 和 MongoDB 不变。
- **管理后台**：保留现有的静态 `admin.html` 方案，不受 Astro 编译影响。

## 2. 迁移目录结构设计
```text
个人博客/
├── api/                     # 保持原样：Vercel Serverless Functions
├── public/                  # Astro 静态资源目录（迁移现有静态资产）
│   ├── admin.html           # 移入此处：保持原样，通过 /admin.html 直接访问
│   ├── style.css            # 移入此处：供 admin 和新页面兼容使用
│   ├── script.js            # 移入此处：供现有页面逻辑兼容使用
│   └── images/              # 移入此处：原有图片目录
├── src/                     # Astro 源码目录（新增）
│   ├── components/          # 提取的可复用组件
│   │   ├── Header.astro     # 顶部导航栏
│   │   ├── Footer.astro     # 底部版权与社交链接
│   │   ├── FloatingMenu.astro # 悬浮操作菜单
│   │   ├── ArticleCard.astro # 最新文章卡片
│   │   └── TwikooComments.astro # Twikoo 评论组件
│   ├── layouts/             # 页面布局
│   │   └── BaseLayout.astro # 包含全局 head、header、footer 的基础布局
│   └── pages/               # 路由页面
│       ├── index.astro      # 重构自原 index.html
│       └── articles.astro   # 重构自原 articles.html
├── astro.config.mjs         # Astro 配置文件（新增）
├── package.json             # 更新：加入 astro 相关依赖
└── vercel.json              # 更新：适配 Astro 和现有 API 的路由
```

## 3. 页面路由设计
迁移后，路由将由 Astro 和 Vercel 共同接管：
- `/` -> 渲染 `src/pages/index.astro`
- `/articles` -> 渲染 `src/pages/articles.astro`
- `/admin.html` -> 直接提供 `public/admin.html` 静态文件
- `/api/*` -> 拦截并交给 Vercel Serverless Functions 执行

## 4. 组件划分设计
为了最大限度复用代码，前端划分为以下组件层次：
- **布局层 (Layout)**: `BaseLayout.astro` 统一管理 HTML 骨架、Meta 标签、全局 CSS 引入和主题初始化脚本。
- **通用 UI 层 (UI Components)**: `Header.astro`（导航栏）、`Footer.astro`（页脚）、`FloatingMenu.astro`（悬浮菜单）。
- **业务组件层 (Feature Components)**: `ArticleCard.astro`（首页文章预览）、`CategoryCard.astro`（知识专栏模块）、`FriendCard.astro`（友情链接模块）。

## 5. 渐进式迁移顺序
为保证迁移过程不影响线上服务，采取以下迁移策略：
1. **基建阶段**：在根目录安装 Astro，建立 `src` 和 `public` 结构。
2. **资产转移**：将 `admin.html`、CSS、JS 和 `images/` 平滑转移至 `public/`，保证后台系统独立运行。
3. **组件抽象**：将 `index.html` 中的通用部分剥离，创建 Layout、Header 和 Footer。
4. **页面重构**：逐个重写 `index.astro` 和 `articles.astro`。第一阶段保留原有的客户端 Fetch 数据逻辑（SPA 体验），暂不改为服务端渲染 (SSR) 或构建时静态生成 (SSG)，以最小化对现有逻辑的破坏。
5. **部署配置适配**：精简并更新 `vercel.json`，利用 Vercel 原生的 Astro 预设，确保 API 路由与页面路由完美共存。
