# 修复博客首页图片不显示问题的计划

## 1. 现状分析 (Current State Analysis)
- 此前已经将 `style.css` 中的图片引用修改为匹配实际文件名的 `1.PNG`，并推送到 GitHub。
- **问题原因**：用户反馈图片仍然没有显示。这通常是因为 **浏览器缓存（Browser Cache）** 或是 **CDN/GitHub Pages 缓存** 的问题。用户的浏览器可能仍在加载旧版本的 `style.css`（里面引用的还是错误的 `1.png`），或者缓存了之前图片加载失败（404）的记录。
- **最佳实践**：在 Web 开发中，为了彻底避免大小写敏感问题并强制刷新用户的本地缓存，最好的做法是重命名文件，并为静态资源添加版本号后缀。

## 2. 计划更改 (Proposed Changes)
为了彻底解决缓存问题并遵循良好的命名规范，计划执行以下步骤：

1. **重命名图片文件**：
   - 使用 `git mv` 将图片文件 `1.PNG` 重命名为全小写的 `hero-bg.png`。
   - *原因*：使用全小写字母和中划线能彻底规避 Windows（不区分大小写）与 GitHub Pages 所在的 Linux 服务器（严格区分大小写）之间的差异问题；全新的文件名可以完全绕过浏览器之前对该图片的任何失败缓存。

2. **更新样式表 (style.css)**：
   - 将 `style.css` 中第 74 行的 `background: url('1.PNG') center/cover no-repeat;` 修改为 `background: url('hero-bg.png') center/cover no-repeat;`。

3. **强制刷新缓存 (Cache Busting)**：
   - 修改项目中所有的 HTML 文件（`index.html`, `admin.html`, `articles.html` 以及 `article1.html` 等文章详情页）。
   - 将引入样式的代码从 `<link rel="stylesheet" href="style.css">` 修改为 `<link rel="stylesheet" href="style.css?v=2">`。
   - *原因*：添加 `?v=2` 查询参数会让浏览器认为这是一个新的文件，从而强制重新下载最新的 CSS 文件，而不再使用本地旧的样式缓存。

4. **提交并推送到 GitHub**：
   - 将上述所有更改提交 (Commit) 并推送到 GitHub 的 `main` 分支，触发 GitHub Pages 重新部署。

## 3. 假设与决定 (Assumptions & Decisions)
- **假设**：图片文件本身没有损坏，且处于项目根目录下。
- **决定**：直接通过重命名文件和增加 CSS 版本号参数来解决。这样用户侧无需学习如何“清理浏览器缓存”或“强制刷新（Ctrl+F5）”，只需普通刷新页面即可看到修复效果。

## 4. 验证步骤 (Verification Steps)
- 计划执行完毕并推送到 GitHub 后，等待 1~2 分钟让 GitHub Pages 完成后台部署。
- 用户在浏览器中普通刷新博客首页，由于引用的样式变成了 `style.css?v=2`，背景图变成了全新的 `hero-bg.png`，图片应立即正常显示。