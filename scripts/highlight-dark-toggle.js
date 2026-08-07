/* global hexo */

'use strict';

// 给暗色代码高亮样式表补上初始的 disabled 属性。
//
// 背景：Fluid 的 layout/_partials/css.ejs 会同时输出两张高亮样式表，
// 但只给它们加了 id，没有给暗色那张加 disabled：
//   <link id="highlight-css"      href="/css/highlight.css" />
//   <link id="highlight-css-dark" href="/css/highlight-dark.css" />
// 而负责切换的 source/js/color-schema.js 里 setHighlightCSS() 只做
// removeAttribute('disabled') / setAttribute('disabled', '')，它假定初始状态
// 就是「暗色那张已被禁用」。前提不成立，两张表便同时生效，后加载的暗色表
// 压住亮色表：亮色模式下代码块拿到的是暗色配色，且两套 token 规则混在一起。
//
// 这里在渲染产物上补回那个初始状态，让运行时的切换逻辑重新成立。
// 不改主题源码是因为 node_modules 不进版本控制，Vercel 每次 npm install 都会冲掉。

// 匹配那张 link。刻意收得很紧：属性值里不允许出现引号或 `>`，
// 只认 Fluid 的 css_ex 实际产出的形状（`<link {ex} rel="stylesheet" href="..." />`，
// 双引号、无用户可控属性）。宽松的 `[^>]*` 会在属性值含 `>` 时（如 data-x="a>b"）
// 提前截断，把 disabled 插进属性值中间，直接写坏 HTML；宁可不匹配也不能改错。
const DARK_LINK = /<link(?:\s+[a-zA-Z-]+(?:=(?:"[^">]*"|'[^'>]*'))?)*\s*\/?>/gi;
const IS_DARK_HIGHLIGHT = /\bid\s*=\s*("|')highlight-css-dark\1/i;
const HAS_DISABLED = /\sdisabled(?=[\s=/>])/i;

hexo.extend.filter.register('after_render:html', function(html) {
  return html.replace(DARK_LINK, function(tag) {
    if (!IS_DARK_HIGHLIGHT.test(tag)) return tag;
    // 幂等：主题将来自己补上了就不再重复插入
    if (HAS_DISABLED.test(tag)) return tag;
    return tag.replace(/\s*\/?>$/, ' disabled$&');
  });
});

