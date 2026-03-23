# 博客项目演进与架构记录

## 架构概览
前端: GitHub Pages 托管，通过 JavaScript 动态渲染内容。
后端: Vercel Serverless Functions (`api/` 目录)。
数据库: MongoDB Atlas (通过 Vercel 接口读写)。
域名: 
- 博客访问: `aoiblog.top`
- API 接口: `api.aoiblog.top`

## 更新记录与踩坑总结

### 2026-03-23
**修改内容**: 修复了在后台管理页面（`admin.html`）尝试发布或删除文章时，出现的 "同步到云端失败: Failed to fetch" 错误。
**演进过程**: 修改了 `api/saveArticle.js`, `api/deleteArticle.js`, `api/getArticles.js` 文件，补充了跨域所需的 `Authorization` 请求头支持。
**踩过的坑**: 
- **CORS 预检请求失败**: 前端在发送带有 `Authorization: Bearer <token>` 的 POST 请求时，浏览器会自动先发送一个 OPTIONS 预检请求。如果后端的响应头 `Access-Control-Allow-Headers` 中没有包含 `Authorization`，浏览器会拦截真正的 POST 请求，并抛出 `Failed to fetch` 的错误，导致前端无法与后端正常通信。
