# 修复移动端文章目录和顶部更多

## 调研结论摘要

### 问题一：文章目录（TOC）在移动端文章页不显示

**根因已确认**：[source/js/aoiblog-home.js](file:///e:/桌面/个人博客/source/js/aoiblog-home.js) 中代码结构有误：

- 第 112-115 行：`if (isPost)` 块正确处理了文章页的纸纹纹理
- 第 117 行：`if (!isHome) return;` 在文章页（`isHome=false`）直接提前返回
- 第 135-231 行：移动端 TOC 的所有代码（`initMobileToc()`、`buildMobileToc()`）定义在第 231 行才调用
- **结果**：文章页在第 117 行直接 `return`，`initMobileToc()` 永远不被执行

**线上验证**：访问 https://www.aoiblog.top/2026/04/02/markdown-yu-fa-bi-ji/ 确认：
- `aoiblog-home.js` 已加载（`hasAoiblogJs: true`）
- `#toc-body` 存在且有 70 个 tocbot 链接
- 但 `#aoi-toc-btn`、`#aoi-toc-overlay`、`#aoi-toc-panel` 均不存在（`hasMobileTocBtn: false`）

### 问题二："顶部更多"（Navbar Toggler）点不开

**经线上实测，导航栏折叠按钮正常工作**：

- 访问文章页，移动端尺寸（375px），点击 navbar toggler，`#mobile-grid-menu` 正常展开/收起
- Fluid 主题的 navbar toggler 由 `boot.js → registerNavbarEvent()` 控制，完全独立于我们自定义的 `aoiblog-home.js`
- 自定义 CSS 仅修改了 navbar 的颜色和背景，未影响点击交互
- 未发现 JS 错误

**可能原因**：用户测试时可能是本地开发环境问题，或浏览器缓存导致旧版自定义 JS 产生了运行时错误（如之前正则替换误删代码时期）

## 当前状态

| 文件 | 状态 |
|------|------|
| `source/js/aoiblog-home.js` | 部署版和本地版相同，存在 TOC 代码位置 bug |
| `source/css/aoiblog-home.css` | 正常，无需修改 |
| `_config.fluid.yml` | 正常，custom_js/custom_css 配置正确 |
| Git 状态 | 工作区干净，仅有 `.trae/documents/fix-homepage-snow-texture.md` 未跟踪 |

## 修复方案

### 唯一的改动：移动 `initMobileToc()` 调用位置

**文件**：[source/js/aoiblog-home.js](file:///e:/桌面/个人博客/source/js/aoiblog-home.js)

**操作**：将第 231 行的 `initMobileToc();` 移到 `if (isPost)` 块内（第 115 行之后、第 116 行之前）。

**修改前**（当前代码结构）：

```javascript
if (isPost) {
    document.body.classList.add('aoiblog-post');
    addPaperTexture();
}                                 // ← 第 115 行结束

if (!isHome) return;              // ← 第 117 行：文章页在此 return！

// ... 首页专属代码（雪花、头像等）...

// ---- Mobile TOC ----
function initMobileToc() { ... }
function buildMobileToc(tocBody) { ... }

initMobileToc();                  // ← 第 231 行：永远到不了这里

})();
```

**修改后**：

```javascript
if (isPost) {
    document.body.classList.add('aoiblog-post');
    addPaperTexture();
    initMobileToc();              // ← 移到此处，文章页专用
}

if (!isHome) return;

// ... 首页专属代码 ...（TOC 函数定义和调用从底部删除）

})();
```

**同时需要**：将 `initMobileToc()` 和 `buildMobileToc()` 函数定义移到 `if (isPost)` 块之前，确保在 `if (isPost)` 块内调用时函数已定义。

**最终完整结构调整**：

```javascript
(function () {
  var path = window.location.pathname.replace(/\/+$/, '') || '/';
  var isHome = path === '/' || /^\/page\/\d+$/.test(path);
  var isPost = /^\/\d{4}\/\d{2}\/\d{2}\//.test(path + '/');

  // ... isDarkTheme(), pickColor(), addPaperTexture(), addSnowCanvas() 函数保持不变 ...

  // ---- Mobile TOC functions ----
  function initMobileToc() { ... }
  function buildMobileToc(tocBody) { ... }

  // ---- Page routing ----
  if (isPost) {
    document.body.classList.add('aoiblog-post');
    addPaperTexture();
    initMobileToc();              // ← 在文章页执行移动端 TOC
  }

  if (!isHome) return;

  document.body.classList.add('aoiblog-home');
  addSnowCanvas();

  if (path !== '/') return;

  // ... 首页头像代码 ...
})();
```

## 验证步骤

1. 本地构建：`npx hexo generate` 或 `npm run build`
2. 启动本地服务：`npx hexo server`
3. 在浏览器中打开任意文章页，调整到移动端尺寸（< 992px）
4. 确认右下角出现 TOC 浮动按钮（带三条横线图标）
5. 点击浮动按钮，确认侧滑面板打开并显示文章目录
6. 点击面板中的目录链接，确认跳转到对应标题位置并关闭面板
7. 点击遮罩层，确认面板关闭
8. 访问首页，确认雪花效果正常
9. 访问首页，确认纸纹纹理正常
10. 点击顶部导航栏折叠按钮，确认九宫格菜单正常展开

## 风险与影响

- **风险**：低。仅移动 TOC 初始化调用位置，不新增/删除逻辑
- **影响范围**：仅文章页（`isPost=true`），不影响首页和分页列表页
- **不涉及**：不修改 CSS、不修改 Fluid 主题文件、不修改 `_config.fluid.yml`

## 关于"顶部更多"的说明

经线上实测，navbar toggler 在文章页移动端正常运作。如果用户在本地环境仍遇到问题，建议：
1. 清除浏览器缓存后重试
2. 确认 `npm run build` 已完成且 `dist/` 为最新产物
3. 检查浏览器控制台是否有 JS 错误
