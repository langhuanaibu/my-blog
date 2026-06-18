---
title: "Git常用命令总结笔记"
date: "2026-04-14"
updated: "2026-04-17"
categories:
  - "技术学习"
old_id: "article_1776182215026"
twikooPath: "article_1776182215026"
---
<h2>Git常用命令总结笔记</h2>
# Git 命令教学笔记

这份笔记偏向 Git 命令的教学和日常查阅，重点解决三个问题：

- Git 的基本概念是什么。
- 常用命令怎么写、什么时候用。
- 日常开发中遇到常见命令行现象时怎么处理。

如果要查看团队开发规范、提交规范、分支管理、上线流程和冲突处理 SOP，请看另一份文档：`Git团队开发规范与冲突处理SOP.md`。

## 1. Git 基础概念

### 1.1 Git 是什么

Git 是一个分布式版本控制工具，用来记录代码或文档的修改历史。它可以帮助你：

- 查看文件改了什么。
- 回到某一次历史版本。
- 在不同分支上并行开发功能。
- 和远端仓库协作，例如 GitLab、GitHub、Gitee。

### 1.2 工作区、暂存区、本地仓库、远端仓库

| 概念 | 含义 | 常见操作 |
| --- | --- | --- |
| 工作区 | 你当前直接编辑文件的目录 | 修改文件、查看 `git diff` |
| 暂存区 | 准备进入下一次提交的内容集合 | `git add`、`git restore --staged` |
| 本地仓库 | 当前电脑里 `.git` 保存的提交历史 | `git commit`、`git log` |
| 远端仓库 | GitLab、GitHub、Gitee 等托管仓库 | `git fetch`、`git pull`、`git push` |

可以简单理解为：

```text
工作区 -> git add -> 暂存区 -> git commit -> 本地仓库 -> git push -> 远端仓库
```

### 1.3 文件状态

| 状态 | 含义 |
| --- | --- |
| `untracked` | 新文件，还没有被 Git 跟踪 |
| `modified` | 文件已修改，但还没有加入暂存区 |
| `staged` | 文件已加入暂存区，等待提交 |
| `committed` | 文件内容已经提交到本地仓库 |

常见流转：

```text
untracked / modified
  -> git add <文件>
staged
  -> git commit
committed
```

### 1.4 常见对象和术语

| 术语 | 含义 |
| --- | --- |
| `commit` | 一次提交记录，包含改动内容、作者、时间和提交说明 |
| `HEAD` | 当前所在提交位置，通常指向当前分支最新提交 |
| `branch` | 分支，用于并行开发不同功能 |
| `remote` | 远端仓库地址，例如 `origin` |
| `origin` | 默认远端仓库名 |
| `tag` | 标签，通常用于标记某次上线版本 |
| `stash` | 临时存档，用于暂存还不想提交的改动 |
| `worktree` | 一个仓库对应多个工作目录，适合同时开发多个分支 |
| `merge` | 合并，把一个分支的改动合入另一个分支 |
| `MR` / `Merge Request` | GitLab 中的合并请求 |

### 1.5 fetch、pull、merge、push 的关系

| 命令 | 作用 | 是否改变当前代码 |
| --- | --- | --- |
| `git fetch origin` | 获取远端最新提交信息 | 不直接改变工作区代码 |
| `git merge origin/master` | 把指定分支合并进当前分支 | 会改变当前分支 |
| `git pull origin master` | 拉取远端并合并，相当于 fetch + merge | 会改变当前分支 |
| `git push origin <分支名>` | 把本地提交推送到远端 | 改变远端分支 |

建议新手先理解并多使用：

```bash
git fetch origin
git merge origin/master
```

这样更容易知道每一步发生了什么。

## 2. 初始化与基础配置

### 2.1 查看 Git 配置

```bash
git config --list
```

查看当前仓库和全局生效的 Git 配置。

```bash
git config --global --list
```

只查看全局配置。

### 2.2 配置用户名和邮箱

```bash
git config --global user.name "你的名字"
git config --global user.email "你的邮箱"
```

用户名和邮箱会写入 commit 记录中，用来标识提交者。

### 2.3 配置 Windows 换行符

```bash
git config --global core.autocrlf true
```

在 Windows 环境中推荐这样配置：

- 提交时把 CRLF 转成 LF。
- 检出代码时把 LF 转成 Windows 常用的 CRLF。

这可以减少不同系统之间因为换行符产生的大量无意义 diff。

### 注：什么是 CRLF 和 LF？

它们是文本文件中换行符的两种编码方式，因操作系统不同而有差异。

| 名称 | 缩写 | 字符表示 | 主要使用系统 |
| :--- | :--- | :--- | :--- |
| **CRLF** | `\r\n` | 回车 + 换行 | Windows |
| **LF** | `\n` | 仅换行 | Linux、macOS |

> **术语解释**：
> - `CR` = Carriage Return (回车 `\r`)
> - `LF` = Line Feed (换行 `\n`)

### 为什么会影响到 Git Diff？

跨平台协作时，换行符差异会导致大量无意义的 diff，主要原因如下：

### 场景示例

假设你在 Windows 上编写了一段 Python 代码，换行符为 CRLF：

```python
def hello():   # 换行符是 CRLF
    print("Hello")   # 换行符是 CRLF
```

提交后，同事在 Linux 上查看该文件。如果 Git 不做任何转换，Linux 系统会多出无法识别的 \r 字符，可能显示为：
```python
def hello():^M   # ^M 代表多余的 \r
    print("Hello")^M
```

###  Diff 噪音的产生过程
1.你在 Windows 上修改了文件的第 2 行代码。

2.同事在 Linux 上打开并保存了该文件（未修改代码内容）。

Linux 编辑器自动将所有 CRLF 转换为 LF。

3.此时对比两个版本：

原文件：CRLF 结尾

新文件：LF 结尾

4.Git Diff 结果：显示整个文件的每一行都被修改了，尽管实际代码没有任何变化。

这就是因为换行符差异而产生的“无意义 diff”。

### 解决方案：Git 的 core.autocrlf 配置
在 Windows 环境中，推荐如下配置：

```bash
git config --global core.autocrlf true
```

#### 配置效果
|操作|行为|目的|
|--|--|--|
|git commit(提交到仓库)|自动将 CRLF → LF	|保证仓库内换行符统一|
|git checkout(检出到工作区)	|自动将 LF → CRLF	|适配 Windows 工具显示|

#### 最终结果
- Git 仓库内：始终使用 LF，实现跨平台统一。
- 本地文件：显示为 CRLF，Windows 系统正常识别。
- Diff 比较：基于仓库内的 LF 进行，不会因换行符差异产生噪音。

#### 其他配置选项
|配置值|适用系统|行为说明|
|---|---|---|
|true|Windows|提交转LF，检出转CRLF|
|input|Linux / macOS	|提交转 LF，检出保持 LF|
|false	|特殊场景	|不做任何转换（需团队统一约定）|

**补充**：现代 Windows 开发环境（如 VS Code、Git Bash 等）大多已良好支持 LF 换行符。如果团队统一约定使用 LF，也可以设置为 false。但对于多数 Windows 用户，true 是最省心的默认配置。

## 3. 常用命令速查表

| 场景 | 命令 | 说明 |
| --- | --- | --- |
| 查看当前状态 | `git status` | 查看工作区和暂存区状态 |
| 精简查看状态 | `git status -s` | 短格式显示改动 |
| 查看当前分支 | `git branch --show-current` | 只输出当前分支名 |
| 查看工作区差异 | `git diff` | 比较工作区和暂存区 |
| 查看暂存区差异 | `git diff --cached` | 比较暂存区和最近一次提交 |
| 不分页查看差异 | `git --no-pager diff --cached` | 直接输出差异，不进入分页器 |
| 添加指定文件 | `git add <文件>` | 把指定文件加入暂存区 |
| 取消暂存 | `git restore --staged <文件>` | 从暂存区撤回，保留工作区修改 |
| 撤销工作区修改 | `git restore <文件>` | 丢弃未暂存的工作区修改 |
| 提交代码 | `git commit` | 打开编辑器填写完整提交信息 |
| 单行提交 | `git commit -m "说明"` | 直接在命令中写提交说明 |
| 查看日志 | `git log --oneline` | 一行展示提交历史 |
| 图形化日志 | `git log --graph --oneline --all` | 查看分支关系 |
| 查看本地分支 | `git branch` | 列出本地分支 |
| 查看全部分支 | `git branch -a` | 列出本地和远端分支 |
| 新建并切换分支 | `git switch -c <分支名>` | 推荐的新写法 |
| 切换分支 | `git switch <分支名>` | 切换到已有分支 |
| 获取远端更新 | `git fetch origin` | 只更新远端引用，不自动合并 |
| 拉取远端分支 | `git pull origin <分支名>` | 拉取并合并远端分支 |
| 推送分支 | `git push origin <分支名>` | 推送本地分支到远端 |
| 首次推送并关联 | `git push -u origin <分支名>` | 建立上游关系 |
| 临时保存修改 | `git stash` | 保存当前已跟踪文件的未提交改动 |
| 保存全部修改 | `git stash push -u -m "说明"` | 包含未跟踪文件 |
| 恢复 stash | `git stash pop` | 恢复最近一次 stash 并删除记录 |

## 4. 常用命令参数解释

很多 Git 命令后面会带参数。参数的作用是改变命令行为，比如“用短格式输出”“显示全部分支”“把分支推送后建立上游关系”。

### 4.1 怎么看命令里的占位符

文档里经常会写：

```bash
git add <文件>
git switch <分支名>
git push origin <分支名>
```

其中：

- `<文件>`：表示替换成真实文件路径，不要把尖括号一起输入。
- `<分支名>`：表示替换成真实分支名。
- `<提交ID>`：表示替换成真实 commit hash。

示例：

```bash
git add src/App.vue
git switch feat/export-select-all
git push origin feat/export-select-all
```

### 4.2 短参数和长参数

Git 中很多参数有短写和长写：

| 短参数 | 长参数 | 含义 |
| --- | --- | --- |
| `-s` | `--short` | 短格式输出 |
| `-a` | `--all` | 显示全部 |
| `-c` | `--create` | 创建 |
| `-m` | 无固定长参数 | 后面跟一段说明文字 |
| `-u` | `--set-upstream` / `--include-untracked` | 含义取决于命令 |

注意：同一个短参数在不同命令里可能含义不同。比如：

- `git push -u origin <分支名>` 中的 `-u` 表示建立上游关系。
- `git stash push -u` 中的 `-u` 表示把未跟踪文件也保存进 stash。

### 4.3 状态查看相关参数

```bash
git status -s
```

参数说明：

- `-s`：`--short` 的简写，表示用短格式输出状态。

适合场景：

- 只想快速看哪些文件改了。
- 不想看 `git status` 的长说明文字。

示例：

```text
 M src/App.vue
A  README.md
?? temp.txt
```

### 4.4 差异查看相关参数

```bash
git diff --cached
```

参数说明：

- `--cached`：查看暂存区和最近一次提交之间的差异。

也就是说，它展示的是“下一次 commit 会提交什么”。

```bash
git --no-pager diff --cached
```

参数说明：

- `--no-pager`：Git 全局参数，表示不要进入分页器，直接把结果输出到终端。
- `diff`：真正执行的 Git 子命令。
- `--cached`：查看暂存区差异。

适合场景：

- 终端里只想直接看完 diff，不想按 `q` 退出分页器。
- 提交前快速检查暂存区。

### 4.5 暂存与恢复相关参数

```bash
git restore --staged <文件>
```

参数说明：

- `--staged`：表示操作暂存区，而不是工作区。

作用：

- 把文件从暂存区撤回工作区。
- 不会丢失文件内容。

对比：

```bash
git restore <文件>
```

这个命令没有 `--staged`，作用是撤销工作区修改，会丢弃未暂存内容。

### 4.6 提交相关参数

```bash
git commit -m "说明"
```

参数说明：

- `-m`：message 的意思，后面直接跟提交说明。

适合场景：

- 提交内容很简单，一句话能说清。

不适合场景：

- 提交内容较复杂，需要写 body 或 footer。

复杂提交更推荐：

```bash
git commit
```

这样会打开编辑器，可以写多行提交说明。

### 4.7 日志相关参数

```bash
git log --oneline
```

- `--oneline`：每个 commit 只显示一行，包含短 hash 和标题。

```bash
git log --graph --oneline --all
```

- `--graph`：用字符图展示分支和合并关系。
- `--oneline`：一行展示一个提交。
- `--all`：显示所有分支的提交，不只看当前分支。

适合场景：

- 查看分支从哪里分出来。
- 查看是否产生 merge commit。
- 查看多个分支之间的历史关系。

### 4.8 分支相关参数

```bash
git branch -a
```

- `-a`：`--all` 的简写，显示本地分支和远端分支。

```bash
git branch --show-current
```

- `--show-current`：只输出当前分支名。

```bash
git switch -c <分支名>
```

- `-c`：create 的意思，创建新分支并切换过去。

```bash
git branch -d <分支名>
git branch -D <分支名>
```

- `-d`：安全删除本地分支，如果分支未合并，Git 会阻止删除。
- `-D`：强制删除本地分支，即使分支未合并也会删除。

注意：`-D` 风险更高，使用前确认分支内容已经合并、推送或不再需要。

### 4.9 远端相关参数

```bash
git remote -v
```

- `-v`：verbose 的意思，显示更详细的远端地址，包括 fetch 和 push 地址。

```bash
git push -u origin <分支名>
```

- `-u`：设置上游分支，完整含义接近 `--set-upstream`。
- `origin`：远端仓库名，通常默认叫 `origin`。
- `<分支名>`：要推送到远端的分支。

建立上游关系后，后续在同一分支通常只需要：

```bash
git push
```

### 4.10 stash 相关参数

```bash
git stash push -u -m "说明"
```

参数说明：

- `push`：创建一条新的 stash 记录。
- `-u`：include untracked，表示把未跟踪文件也保存进去。
- `-m`：message，给这条 stash 写说明，方便以后识别。

常见子命令区别：

| 命令 | 含义 |
| --- | --- |
| `git stash list` | 查看 stash 列表 |
| `git stash apply` | 恢复 stash，但保留 stash 记录 |
| `git stash pop` | 恢复 stash，并删除该 stash 记录 |
| `git stash drop stash@{0}` | 删除指定 stash |
| `git stash clear` | 清空所有 stash |

注意：`git stash clear` 风险较高，会清空全部 stash 记录。

### 4.11 reset 相关参数

`git reset` 主要影响三个位置：

- `HEAD`：当前提交指针。
- 暂存区：已经 `git add` 的内容。
- 工作区：你正在编辑的文件。

| 命令 | HEAD | 暂存区 | 工作区 | 风险 |
| --- | --- | --- | --- | --- |
| `git reset --soft HEAD^` | 回退 | 保留 | 保留 | 较低 |
| `git reset --mixed HEAD^` | 回退 | 取消暂存 | 保留 | 中等 |
| `git reset --hard HEAD^` | 回退 | 丢弃 | 丢弃 | 高 |

参数说明：

- `--soft`：只移动 HEAD，保留暂存区和工作区。
- `--mixed`：移动 HEAD，并重置暂存区，工作区内容保留。
- `--hard`：移动 HEAD，重置暂存区和工作区，会丢弃改动。
- `HEAD^`：表示当前提交的上一个提交。

注意：`--hard` 是高风险参数，不确定时先 `git stash push -u -m "backup-before-reset"`。

### 4.12 worktree 相关参数

```bash
git worktree add <目录> -b <分支名> master
```

参数说明：

- `add`：新增一个工作区。
- `<目录>`：新工作区要放到哪里。
- `-b <分支名>`：创建一个新分支。
- `master`：新分支从哪个基准分支拉出来。

示例：

```bash
git worktree add .worktrees/export-select-all -b feat/export-select-all master
```

含义：

- 新建目录 `.worktrees/export-select-all`。
- 创建并检出分支 `feat/export-select-all`。
- 该分支基于 `master`。

### 4.13 高风险参数提醒

| 参数或命令 | 风险 | 建议 |
| --- | --- | --- |
| `--hard` | 丢弃工作区和暂存区改动 | 执行前先 stash 或确认不需要 |
| `-D` | 强制删除本地分支 | 确认分支已合并或不再需要 |
| `git stash clear` | 清空所有 stash | 优先用 `git stash drop stash@{n}` |
| `git push --force` | 覆盖远端历史，影响他人 | 公共分支不要随便使用 |
| `git restore <文件>` | 丢弃未暂存修改 | 不确定时先备份或 stash |

## 5. 状态与差异查看

### 5.1 查看当前状态

```bash
git status
```

用于查看：

- 当前在哪个分支。
- 哪些文件被修改。
- 哪些文件已经暂存。
- 是否有未跟踪文件。

短格式：

```bash
git status -s
```

参数拆解：

- `status`：查看当前仓库状态。
- `-s`：用 short 短格式显示，只保留关键状态码和文件名。

常见状态示例：

```text
 M app.js
A  readme.md
?? temp.txt
```

含义：

- ` M`：文件在工作区被修改，但未暂存。
- `A `：新文件已经暂存。
- `??`：未跟踪文件。

### 5.2 查看工作区差异

```bash
git diff
```

查看工作区相对暂存区的改动。也就是：你已经改了但还没有 `git add` 的内容。

### 5.3 查看暂存区差异

```bash
git diff --cached
```

查看暂存区相对最近一次提交的改动。也就是：下一次 commit 会提交什么。

如果不想进入分页器，可以用：

```bash
git --no-pager diff --cached
```

参数拆解：

- `--no-pager`：不使用分页器，直接输出结果。
- `diff`：查看差异。
- `--cached`：查看暂存区里的差异。

## 6. 暂存与提交

### 6.1 添加指定文件到暂存区

```bash
git add <文件>
```

示例：

```bash
git add src/App.vue
git add package.json
```

建议优先按文件添加，避免不小心把无关改动一起提交。

### 6.2 不推荐默认使用 git add .

```bash
git add .
```

这个命令会把当前目录下所有改动加入暂存区。它很方便，但容易把调试文件、临时文件、无关修改一起提交。

更推荐：

```bash
git status
git add <文件1>
git add <文件2>
git --no-pager diff --cached
git commit
```

### 6.3 取消暂存

```bash
git restore --staged <文件>
```

这个命令只会把文件从暂存区撤回工作区，不会丢失修改。

### 6.4 提交代码

打开编辑器填写完整提交信息：

```bash
git commit
```

简单提交：

```bash
git commit -m "docs: update git notes"
```

参数拆解：

- `commit`：把暂存区内容提交到本地仓库。
- `-m`：message，后面跟本次提交说明。
- `"docs: update git notes"`：提交说明内容。

如果提交内容较多，建议使用 `git commit` 打开编辑器，写清楚标题、正文和备注。

## 7. 查看提交历史

### 7.1 简洁日志

```bash
git log --oneline
```

示例：

```text
3f2a1b0 docs: update git notes
9c8d7e6 fix: correct login redirect
```

### 7.2 图形化查看分支历史

```bash
git log --graph --oneline --all
```

参数拆解：

- `--graph`：显示分支和合并的字符图。
- `--oneline`：每个提交压缩成一行。
- `--all`：显示所有分支的历史。

适合查看：

- 分支从哪里拉出来。
- merge commit 在哪里。
- 多个分支之间的提交关系。

### 7.3 查看两个提交之间的差异

```bash
git diff <提交ID1> <提交ID2>
```

示例：

```bash
git diff 3f2a1b0 9c8d7e6
```

## 8. 分支命令

### 8.1 查看分支

```bash
git branch
```

查看本地分支。

```bash
git branch -a
```

查看本地和远端分支。

参数拆解：

- `branch`：查看或管理分支。
- `-a`：all，显示全部分支，包括远端跟踪分支。

### 8.2 查看当前分支名

```bash
git branch --show-current
```

### 8.3 新建并切换分支

```bash
git switch -c <分支名>
```

参数拆解：

- `switch`：切换分支。
- `-c`：create，创建新分支。
- `<分支名>`：新分支的名字，使用时替换成真实分支名。

示例：

```bash
git switch -c feat/export-select-all
```

### 8.4 切换到已有分支

```bash
git switch <分支名>
```

示例：

```bash
git switch master
```

### 8.5 删除本地分支

```bash
git branch -d <分支名>
```

安全删除：如果分支还没有被合并，Git 会阻止删除。

```bash
git branch -D <分支名>
```

强制删除：会直接删除本地分支。使用前确认分支内容已经不需要，或已经推送到远端。

## 9. 远端仓库命令

### 9.1 查看远端地址

```bash
git remote -v
```

示例：

```text
origin  git@gitlab.example.com:team/project.git (fetch)
origin  git@gitlab.example.com:team/project.git (push)
```

### 9.2 获取远端最新信息

```bash
git fetch origin
```

这个命令只更新远端引用，例如 `origin/master`，不会自动修改当前工作区代码。

### 9.3 拉取远端分支

```bash
git pull origin <分支名>
```

示例：

```bash
git pull origin master
```

它相当于：

```bash
git fetch origin
git merge origin/master
```

### 9.4 推送分支到远端

首次推送：

```bash
git push -u origin <分支名>
```

参数拆解：

- `push`：把本地提交推送到远端。
- `-u`：建立本地分支和远端分支的上游关系。
- `origin`：远端仓库名。
- `<分支名>`：要推送的分支名。

示例：

```bash
git push -u origin feat/export-select-all
```

`-u` 表示建立本地分支和远端分支的上游关系。建立后，后续通常直接：

```bash
git push
```

### 9.5 GitLab 页面看不到本地分支的原因

GitLab 只能看到远端分支，看不到你电脑上的本地分支。

如果你本地新建了分支，但 GitLab 的 source branch 下拉框里看不到，需要先推送：

```bash
git push -u origin <分支名>
```

## 10. Stash 临时存档

### 10.1 stash 适合什么场景

stash 用于临时保存未提交改动，适合：

- 当前功能做到一半，需要切换分支处理别的任务。
- 当前改动还不能提交，但又不想丢。
- 本地分支上混入多个功能，需要先保存再拆分。

### 10.2 保存当前修改

只保存已跟踪文件的修改：

```bash
git stash
```

保存所有修改，包括未跟踪文件：

```bash
git stash push -u -m "临时说明"
```

参数拆解：

- `stash`：临时保存未提交改动。
- `push`：创建一条新的 stash 记录。
- `-u`：把未跟踪文件也一起保存。
- `-m`：给 stash 写说明。

示例：

```bash
git stash push -u -m "before-switch-branch"
```

### 10.3 查看 stash 记录

```bash
git stash list
```

示例：

```text
stash@{0}: On feat/export-select-all: before-switch-branch
stash@{1}: On master: temp-save-before-splitting-features
```

### 10.4 恢复 stash

恢复最近一次 stash，但保留 stash 记录：

```bash
git stash apply
```

恢复最近一次 stash，并删除该 stash 记录：

```bash
git stash pop
```

恢复指定 stash：

```bash
git stash apply stash@{1}
```

### 10.5 从 stash 中恢复指定文件

```bash
git checkout stash@{0} -- <文件路径>
```

示例：

```bash
git checkout stash@{0} -- src/App.vue
```

### 10.6 删除 stash

删除指定 stash：

```bash
git stash drop stash@{0}
```

清空全部 stash：

```bash
git stash clear
```

注意：`git stash clear` 会清空所有 stash 记录，操作前一定确认不再需要这些临时改动。

## 11. 恢复与回退

### 11.1 撤销工作区修改

```bash
git restore <文件>
```

作用：丢弃指定文件在工作区中的未暂存修改。

示例：

```bash
git restore src/App.vue
```

注意：这个命令会丢弃修改，执行前确认文件内容不需要保留。

### 11.2 取消暂存

```bash
git restore --staged <文件>
```

作用：把文件从暂存区撤回工作区，修改还在。

### 11.3 回退上一次提交但保留暂存区

```bash
git reset --soft HEAD^
```

参数拆解：

- `reset`：移动当前分支指针，并按参数决定是否影响暂存区和工作区。
- `--soft`：只回退提交记录，保留暂存区和工作区。
- `HEAD^`：当前提交的上一个提交。

适合：刚提交完，发现 commit message 写错，或者想重新组织提交。

### 11.4 回退上一次提交并取消暂存

```bash
git reset --mixed HEAD^
```

适合：想撤销最近一次提交，把改动重新放回工作区整理。

### 11.5 强制回退并丢弃修改

```bash
git reset --hard HEAD^
```

作用：回到上一个提交，并丢弃工作区和暂存区内容。

注意：这是高风险命令。除非你非常确定这些改动不需要，否则不要随便使用。

## 12. Worktree 多工作区

### 12.1 worktree 是什么

worktree 可以让一个 Git 仓库同时拥有多个工作目录。每个工作目录可以对应不同分支。

适合场景：

- 同时开发多个功能。
- 一个功能还没做完，又要处理另一个分支的问题。
- 不想频繁 stash 和切换分支。

### 12.2 新建 worktree

```bash
git worktree add <目录> -b <分支名> master
```

参数拆解：

- `worktree add`：新增一个独立工作区。
- `<目录>`：新工作区的目录。
- `-b <分支名>`：创建新分支并让新工作区使用它。
- `master`：新分支基于哪个分支创建。

示例：

```bash
git worktree add .worktrees/export-select-all -b feat/export-select-all master
```

含义：

- `.worktrees/export-select-all`：新工作区目录。
- `-b feat/export-select-all`：创建新分支。
- `master`：从 master 拉出新分支。

### 12.3 查看 worktree

```bash
git worktree list
```

输出示例：

```text
C:/Users/lenovo/Desktop/BPMAX/hpt-frontend                                [master]
C:/Users/lenovo/Desktop/BPMAX/hpt-frontend/.worktrees/export-select-all   [feat/export-select-all]
```

注意：你在哪个目录启动项目，运行的就是哪个目录对应分支的代码。

## 13. 日常操作示例

### 13.1 第一次配置 Git

```bash
git config --global user.name "你的名字"
git config --global user.email "你的邮箱"
git config --global core.autocrlf true
git config --global --list
```

### 13.2 新建分支开发

```bash
git switch master
git pull origin master
git switch -c feat/demo-feature
```

### 13.3 分文件提交

```bash
git status
git add src/App.vue
git add src/components/Demo.vue
git --no-pager diff --cached
git commit
```

### 13.4 查看提交历史

```bash
git log --oneline
git log --graph --oneline --all
```

### 13.5 临时保存未完成代码

```bash
git stash push -u -m "before-fix-urgent-bug"
git switch hotfix/urgent-bug
```

恢复：

```bash
git switch feat/demo-feature
git stash pop
```

### 13.6 本地分支推送到 GitLab

```bash
git push -u origin feat/demo-feature
```

后续同一个分支继续提交后：

```bash
git push
```

### 13.7 从 stash 中恢复指定文件

```bash
git stash list
git checkout stash@{0} -- src/App.vue
```

### 13.8 使用 worktree 同时开发多个功能

```bash
git switch master
git pull origin master
git worktree add .worktrees/feature-a -b feat/feature-a master
git worktree add .worktrees/feature-b -b feat/feature-b master
```

之后分别进入不同目录开发：

```powershell
cd C:\Users\lenovo\Desktop\BPMAX\hpt-frontend\.worktrees\feature-a
```

## 14. 命令行常见现象

### 14.1 git diff 后终端像卡住了

大概率是进入了分页器。按：

```text
q
```

即可退出。

如果不想进入分页器，可以使用：

```bash
git --no-pager diff
git --no-pager diff --cached
```

### 14.2 git commit 打开 vim 后怎么写

提交信息要写在最上方，写在 `#` 注释行上面。

如果打开的是 vim：

1. 按 `gg` 跳到顶部。
2. 按 `O` 在顶部上方插入一行。
3. 输入 commit message。
4. 按 `Esc`。
5. 输入 `:wq`。
6. 按回车保存退出。

如果不想进入编辑器，可以使用：

```bash
git commit -m "docs: update git notes"
```

### 14.3 出现 E163: 只有一个文件可编辑

这通常只是 vim 的提示，不代表提交失败。

处理方式：

1. 按 `Enter`。
2. 继续输入 `:wq`。
3. 按回车保存退出。

### 14.4 GitLab 看不到本地分支

原因：分支只存在你的电脑上，还没有推送到远端。

解决：

```bash
git push -u origin <分支名>
```

推送后，GitLab 的 source branch 下拉框才能看到该分支。

## 15. 学习建议

新手可以按这个顺序掌握 Git：

1. 先理解工作区、暂存区、本地仓库、远端仓库。
2. 熟练使用 `git status` 和 `git diff`，知道自己改了什么。
3. 养成按文件 `git add` 的习惯。
4. 提交前用 `git --no-pager diff --cached` 检查暂存区。
5. 学会新建分支、切换分支、推送分支。
6. 学会用 `stash` 临时保存未完成代码。
7. 再学习 `merge`、冲突处理和 worktree。

日常开发最常用的一组命令是：

```bash
git status
git diff
git add <文件>
git --no-pager diff --cached
git commit
git push
```



<section class="legacy-comments">
  <h2>评论区</h2>
  <div id="twikoo-article_1776182215026" data-twikoo-path="article_1776182215026"></div>
</section>
