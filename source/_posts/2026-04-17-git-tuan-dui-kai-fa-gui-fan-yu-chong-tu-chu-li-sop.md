---
title: "Git 团队开发规范与冲突处理 SOP"
date: "2026-04-17"
updated: "2026-04-17"
categories:
  - "技术学习"
index_img: "/images/covers/defaults/technology-learning.webp"
old_id: "article_1776429194802"
twikooPath: "article_1776429194802"
---
<h2>Git 团队开发规范与冲突处理 SOP</h2>
2026年4月17日20:37:25<br>
好不容易提前把今天的工作弄完了，遂拷打ai根据这几天拷打ai的经验生成了两篇如何使用git的笔记<br>
上班好累……<br>

这份文档偏向真实项目协作，重点说明团队中的开发规范、提交规范、分支管理、开发流程、上线流程、合并冲突处理和常见问题。

如果要学习 Git 基础概念和常用命令，请先看：`Git常用命令总结笔记.md`。

## 1. 核心原则

团队协作时，Git 的目标不是“把代码提交上去就行”，而是保证每次提交、每个分支、每次合并都清楚、可追踪、可回滚。

日常开发遵循以下原则：

- 操作分支前，始终保证本地仓库已经同步远端最新代码。
- 本地不要长期留有大量未提交代码。
- 一般情况下禁止使用 `git add .` 提交全量文件，优先按文件或功能分批提交。
- 提交要小步、清晰、可回看，不要把多个无关功能混在一个 commit 中。
- 每天下班前至少提交一次代码，避免本地改动丢失。
- 如果代码还不稳定，可以先提交到本地，开发完成后再推送远端。
- 大块功能改动应在独立功能分支或 worktree 中开发，开发完再合并回目标分支。
- 公共分支上谨慎使用 `rebase`，禁止随意强推。
- 危险命令执行前必须确认影响范围，例如 `git reset --hard`、`git stash clear`、`git push --force`。

## 2. 开发前检查

开始任何开发前，先确认仓库、分支和工作区状态。

```bash
git status --short --branch
git branch --show-current
git fetch origin
```

如果准备从 `master` 新建功能分支，应先同步本地 `master`：

```bash
git switch master
git pull origin master
```

如果项目使用 worktree，先确认当前功能分支实际所在目录：

```bash
git worktree list
```

注意：启动哪个目录，运行的就是哪个目录对应分支的代码。不要在主工作区启动项目，却以为跑的是 `.worktrees` 里的功能分支代码。

## 3. Commit 提交规范

### 3.1 标准格式

推荐提交信息格式：

```text
type(scope): subject

body

footer
```

由三部分组成：

- 标题行：必填，描述主要修改类型和内容。
- 主题内容：说明为什么修改、做了什么修改、开发思路是什么。
- 页脚注释：可选，可写备注、BUG 号、Closed Issues 或 BREAKING CHANGE。

### 3.2 标题行

标题行格式：

```text
type(scope): subject
```

说明：

- `type`：必填，表示 commit 类型。
- `scope`：可选，表示影响范围，例如 `global`、`common`、`route`、`component`、`utils`、`build`。
- `subject`：必填，简短描述本次提交内容，建议不超过 50 个字符。

示例：

```text
feat(component): add export button
fix(route): correct login redirect
docs: update git workflow notes
```

### 3.3 type 类型

| type | 说明 |
| --- | --- |
| `feat` | 新功能、新特性 |
| `fix` | 修复 bug |
| `perf` | 性能优化 |
| `refactor` | 代码重构，不改变外部行为 |
| `docs` | 文档修改 |
| `style` | 代码格式修改，不是 CSS 样式修改 |
| `test` | 测试用例新增或修改 |
| `build` | 项目构建或依赖项修改 |
| `revert` | 回滚上一次提交 |
| `ci` | 持续集成相关修改 |
| `chore` | 其他不属于以上类型的修改 |
| `release` | 发布新版本 |
| `workflow` | 工作流相关修改 |

### 3.4 body 正文

当提交内容不止一两行时，建议写 body。

body 应说明：

- 为什么要改。
- 改了哪些关键点。
- 有哪些实现思路或取舍。
- 是否影响已有功能。

示例：

```text
fix(component): preserve line breaks in approval comments

Approval comments lost line breaks after rendering as plain text.
This change keeps the existing image rendering component and adds
white-space: pre-wrap for text comments.
```

### 3.5 footer 页脚

footer 通常用于：

- 关联 BUG 编号。
- 关闭 issue。
- 标记破坏性变更。

示例：

```text
Closed #123
```

或：

```text
BREAKING CHANGE: remove legacy export API
```

### 3.6 常见提交示例

新功能：

```text
feat(export): add select all export support

Add export support for selected project records.
```

修复 bug：

```text
fix(login): correct redirect after session timeout

Keep the original redirect URL before sending users to login.
```

文档：

```text
docs: add git team workflow sop
```

重构：

```text
refactor(utils): simplify date formatter

Keep the original output format while removing duplicated branches.
```

合并最新 master 并解决冲突：

```text
chore: merge latest master and resolve conflicts
```

## 4. 分支管理规范

### 4.1 master 稳定分支

`master` 是稳定分支。

规则：

- 代码至少上过一次客户生产环境后，才可以合并入此分支。
- 只允许通过 MR 合入代码。
- 不允许直接推送。

用途：

- 表示稳定、可追踪的生产基础代码。
- 作为新功能分支的常用起点。
- 上线后由 release 分支合回。

### 4.2 development 开发测试分支

`development` 是开发测试分支。

规则：

- 功能开发完成后合并入此分支提测到测试环境。
- 所有客户测试环境都会部署此分支。
- 只允许通过 MR 合入代码。
- 不允许直接推送。

用途：

- 承接功能分支的提测代码。
- 测试同学验证开发阶段功能。

### 4.3 release 预发分支

命名规则：

```text
release/<客户标识>_<月_日>
```

示例：

```text
release/cbd_12_11
```

含义：茶百道 12 月 11 日上线功能的预发分支。

用途：

- 功能经过测试同学验证完成后，合入预发分支。
- 用于部署预发环境。
- 上线时通常部署对应 release 分支代码。

### 4.4 feat 功能分支

命名规则：

```text
feat/<英文功能名称>
```

示例：

```text
feat/export-select-all
feat/cbd-detail-multiline-display
```

规则：

- 新功能开发分支。
- 一般从最新 `master` 检出。
- 一个功能尽量一个分支。
- 可以多次 commit、多次 push。
- Code review 后继续在同一分支修复，原 MR 会自动更新。

### 4.5 hotfix 热修复分支

命名规则：

```text
hotfix/<问题名称>
```

规则：

- 上线后出现紧急 bug 时使用。
- 基于最近一次对应客户上线 tag 检出热修复分支。
- 修复完成后按新功能提测流程走。

### 4.6 Tag 规范

每次客户上线完成后，需要基于 release 分支创建对应 tag，用于标识客户上线时各仓库代码状态，方便出问题时回滚。

命名规则：

```text
<客户标识>_<年_月_日>
```

示例：

```text
cbd_2026_04_17
```

说明：

- 除 `bpmax-plugins` 外，其他项目通常会在包哥部署生产环境时自动生成 tag。
- `bpmax-plugins` 需要在 release 分支上手动创建 tag。

## 5. 标准开发流程

### 5.1 开发新功能

从对应项目最新 `master` 分支检出新功能分支：

```bash
git switch master
git pull origin master
git switch -c feat/<英文功能名称>
```

开发过程中：

- 尽量按功能点拆分提交。
- 不要把多个无关功能混在同一个分支或同一个 commit 中。
- 提交前检查暂存区内容。

推荐提交流程：

```bash
git status
git add <文件1>
git add <文件2>
git --no-pager diff --cached
git commit
```

### 5.2 新功能提测

本地开发完成后，达到提测标准再提测。

提测标准通常包括：

- 功能主体开发完成。
- 自测通过。
- 冒烟测试通过。
- 没有明显控制台错误或阻塞问题。
- 提交信息符合规范。

提测流程：

1. 推送功能分支到远端。
2. 创建 MR 合并到 `development`。
3. 找相关负责人合并。
4. 部署测试环境时，可找相关负责人协助部署。

首次推送：

```bash
git push -u origin feat/<英文功能名称>
```

后续同分支推送：

```bash
git push
```

### 5.3 测试阶段出现 bug

如果测试阶段发现 bug：

1. 回到原功能分支修复。
2. 提交修复 commit。
3. 推送同一个功能分支。
4. 再次合并入 `development`。
5. 重复提测流程。

不要为了同一个功能的测试 bug 随意新建多个功能分支，除非确实是独立功能或独立问题。

### 5.4 线上紧急 bug 修复

线上出现紧急 bug 时：

1. 找到最近一次对应客户上线 tag。
2. 从该 tag 检出 `hotfix` 分支。
3. 在 `hotfix` 分支修复问题。
4. 修复完成后按新功能提测流程走。

示例：

```bash
git fetch origin --tags
git switch -c hotfix/<问题名称> <tag名称>
```

### 5.5 预上线

预上线前，将各个功能分支合并到对应预发分支。

流程：

1. 从合适基线创建或更新 `release/<客户标识>_<月_日>`。
2. 将本次要上线的功能分支合入 release。
3. 部署预发环境。
4. 测试同学在预发环境验证。

预发环境发现问题时：

- 回到对应功能分支修复。
- 修复后再合入预发分支。
- 不建议直接在 release 分支上堆临时修复，避免功能来源不清晰。

### 5.6 上线

上线时：

- 有迭代功能的项目，上对应预发分支代码。
- 本次没有迭代功能的项目，上对应 `master` 分支代码。

上线前确认：

- release 分支内容符合本次上线范围。
- 预发测试通过。
- 关键功能冒烟通过。
- 需要上线的仓库和分支明确。

### 5.7 上线后操作

上线后必须做收尾：

1. 确保预发分支已经加上 tag。
2. 合并预发分支到 `master`。
3. 合并 `master` 分支到 `development`。
4. 删除预发分支对应的各个功能分支。
5. 删除预发分支。

这样可以保证：

- `master` 记录已上线稳定代码。
- `development` 不会落后于生产稳定代码。
- 临时分支及时清理，避免后续误用。

## 6. MR 与推送规范

### 6.1 首次推送分支

本地新建分支后，GitLab 页面看不到该分支。必须先推送到远端：

```bash
git push -u origin <分支名>
```

示例：

```bash
git push -u origin feat/export-select-all
```

`-u` 会建立本地分支和远端分支的上游关系。

### 6.2 后续推送

建立上游关系后，后续同分支直接：

```bash
git push
```

### 6.3 已有 open MR

如果 GitLab 提示：

```text
Another open merge request already exists for this source branch
```

说明这个源分支已经有一个未关闭 MR。

处理方式：

- 不要重复新建 MR。
- 继续 push 到同一个分支。
- 原 MR 会自动更新。

### 6.4 MR 目标分支

常见目标分支：

| 场景 | 源分支 | 目标分支 |
| --- | --- | --- |
| 新功能提测 | `feat/<功能名>` | `development` |
| 预上线 | `feat/<功能名>` | `release/<客户标识>_<月_日>` |
| 上线后合回 | `release/<客户标识>_<月_日>` | `master` |
| 同步开发分支 | `master` | `development` |

创建 MR 前，必须确认 source branch 和 target branch 没选反。

## 7. 合并冲突处理 SOP

本 SOP 用于处理 GitLab MR 提示 merge conflict 的常见场景。

核心原则：

1. 先让本地 `master` 同步到线上最新 `origin/master`。
2. 再把最新 `origin/master` 合并到发生冲突的功能分支。
3. 在本地解决冲突。**一定要在线下解决冲突，不要线上解决**
4. 验证后推送功能分支，让 MR 自动更新。

### 7.1 确认当前仓库和分支

进入目标仓库或目标 worktree：

```powershell
cd C:\Users\lenovo\Desktop\BPMAX\hpt-frontend
```

查看当前分支和工作区：

```bash
git status --short --branch
git branch --show-current
```

如果项目使用 worktree：

```bash
git worktree list
```

如果看到类似：

```text
C:/Users/lenovo/Desktop/BPMAX/hpt-frontend/.worktrees/cbd-detail-multiline-display  [feat/cbd-detail-multiline-display]
```

后续操作应进入该 worktree：

```powershell
cd C:\Users\lenovo\Desktop\BPMAX\hpt-frontend\.worktrees\cbd-detail-multiline-display
```

### 7.2 同步本地 master 到线上最新 master

先更新远端引用：

```bash
git fetch origin
```

确认本地 `master` 和线上 `origin/master` 的差异：

```bash
git rev-list --left-right --count master...origin/master
```

输出格式：

```text
本地领先数  本地落后数
```

例如：

```text
0  65
```

表示本地 `master` 落后线上 `origin/master` 65 个提交。

切到 `master`：

```bash
git switch master
```

如果 `master` 上有未提交改动，先临时保存：

```bash
git stash push -u -m "before-sync-master"
```

快进同步到线上最新：

```bash
git merge --ff-only origin/master
```

如果前面 stash 过，再恢复：

```bash
git stash pop
```

最后确认本地 `master` 已经和线上一致：

```bash
git rev-list --left-right --count master...origin/master
```

期望输出：

```text
0  0
```

注意：把 `origin/master` 同步到本地 `master` 不会影响线上。只有执行 `git push origin master` 才会改变线上 `master`。

### 7.3 切回发生冲突的功能分支

如果功能分支在当前仓库：

```bash
git switch feat/<功能分支>
```

如果功能分支在 worktree：

```powershell
cd C:\Users\lenovo\Desktop\BPMAX\hpt-frontend\.worktrees\<功能worktree目录>
```

再次确认：

```bash
git status --short --branch
git branch --show-current
```

### 7.4 合并最新 origin/master 到功能分支

如果功能分支上有未提交改动，先 stash：

```bash
git stash push -u -m "before-merge-master-into-feature"
```

确保远端引用最新：

```bash
git fetch origin
```

在功能分支上合并线上最新 `master`：

```bash
git merge origin/master
```

如果没有冲突，Git 会直接完成合并。

如果有冲突，Git 会提示类似：

```text
CONFLICT (content): Merge conflict in components/ProjectStepSingle/ProjectStepSingle.vue
Automatic merge failed; fix conflicts and then commit the result.
```

### 7.5 查看冲突文件和冲突块

查看所有未解决冲突文件：

```bash
git diff --name-only --diff-filter=U
```

查看工作区状态：

```bash
git status --short --branch
```

状态中 `UU` 表示该文件有未解决冲突：

```text
UU components/ProjectStepSingle/ProjectStepSingle.vue
```

在 PowerShell 中搜索冲突标记：

```powershell
Select-String -Path "components\ProjectStepSingle\ProjectStepSingle.vue" -Pattern "<<<<<<<|=======|>>>>>>>" -Context 5,5
```

冲突块通常长这样：

```text
<<<<<<< HEAD
当前功能分支的内容
=======
合并进来的 origin/master 内容
>>>>>>> origin/master
```
可视化理解:
```text
文件内容
    │
    ▼
<<<<<<< HEAD      ← 冲突开始，下面是“你的版本”
你的代码 A
你的代码 B
=======           ← 分隔线，下面是“别人的版本”
别人的代码 A
别人的代码 B
>>>>>>> main      ← 冲突结束，并标明别人的分支名
    │
    ▼
（删除所有标记，保留最终代码）
```
在“功能分支合并 `origin/master`”这个场景中：

- `HEAD` / `ours`：当前功能分支。
- `origin/master` / `theirs`：线上最新 master。

### 7.6 判断解决策略

不要机械地只选一边。先判断两边改动目的。

常见选择：

```bash
# 完全保留当前功能分支版本
git checkout --ours -- path/to/file

# 完全采用 origin/master 版本
git checkout --theirs -- path/to/file
```

但如果两边都有价值，应手动合并。

示例：

- 功能分支改动：保留多行文本输入展示效果，使用 `v-text` 和 `white-space: pre-wrap`。
- `origin/master` 改动：新增 `StepApprovalCommentContent`，支持审批意见中展示图片。

正确策略不是只保留一边，而是合并能力：

- 普通多行文本字段保留功能分支实现。
- 审批意见内容保留线上组件，以支持图片。
- 修改线上组件文本样式为 `white-space: pre-wrap`，保证纯文本审批意见也按输入换行显示。

### 7.7 手动解决冲突

打开冲突文件，删除冲突标记：

```text
<<<<<<< HEAD
=======
>>>>>>> origin/master
```

保留或组合需要的代码。

解决后再次检查是否还有冲突标记：

```powershell
Select-String -Path "components\ProjectStepSingle\ProjectStepSingle.vue" -Pattern "<<<<<<<|=======|>>>>>>>"
```

如果没有输出，说明该文件中没有残留冲突标记。

再检查 Git 是否还有未解决冲突文件：

```bash
git diff --name-only --diff-filter=U
```

如果没有输出，说明冲突都已解决。

### 7.8 标记冲突已解决

把解决后的文件加入暂存区：

```bash
git add -- components/ProjectStepSingle/ProjectStepSingle.vue
```

如果还改了相关组件，也一起加入：

```bash
git add -- components/ProjectStepSingle/ProjectStepSingle.vue components/StepApprovalCommentContent.vue
```

查看状态：

```bash
git status --short --branch
```

如果不再有 `UU`，说明 Git 已接受冲突解决结果。

### 7.9 运行验证

先做 Git 基础检查：

```bash
git diff --check
git diff --name-only --diff-filter=U
```

含义：

- `git diff --check`：检查空白错误。
- `git diff --name-only --diff-filter=U`：确认没有未解决冲突文件。

针对冲突相关文件运行 lint：

```powershell
.\node_modules\.bin\eslint.cmd components/ProjectStepSingle/ProjectStepSingle.vue components/StepApprovalCommentContent.vue
```

如果 worktree 里没有可用的 `node_modules`，可以使用主仓库里的 eslint：

```powershell
C:\Users\lenovo\Desktop\BPMAX\hpt-frontend\node_modules\.bin\eslint.cmd components/ProjectStepSingle/ProjectStepSingle.vue components/StepApprovalCommentContent.vue
```

如果只是 Prettier 或行尾格式问题，可只对相关文件自动修复：

```powershell
C:\Users\lenovo\Desktop\BPMAX\hpt-frontend\node_modules\.bin\eslint.cmd --fix components/ProjectStepSingle/ProjectStepSingle.vue components/StepApprovalCommentContent.vue
```

修复后重新暂存：

```bash
git add -- components/ProjectStepSingle/ProjectStepSingle.vue components/StepApprovalCommentContent.vue
```

### 7.10 提交 merge commit

正常提交：

```bash
git commit -m "chore: merge latest master and resolve conflicts"
```

如果团队要求中文提交，也可以：

```bash
git commit -m "chore: 合并最新master并解决冲突"
```

如果 pre-commit hook 因为无关历史问题阻塞，例如 `origin/master` 自带旧 lint 问题，而冲突相关文件已经单独验证通过，可以谨慎使用：

```bash
git commit --no-verify -m "chore: 合并最新master并解决冲突"
```

使用 `--no-verify` 前必须确认：

- 冲突文件已解决。
- `git diff --check` 通过。
- 冲突相关文件 lint 通过。
- 阻塞 hook 的问题不是本次改动引入。

### 7.11 恢复合并前 stash 的本地改动

如果合并前做过 stash，提交 merge commit 后恢复：

```bash
git stash list
git stash pop
```

如果 `stash pop` 又产生冲突，按同样流程解决。

恢复完成后确认工作区：

```bash
git status --short --branch
```

如果输出类似：

```text
## feat/your-feature-branch...origin/feat/your-feature-branch [ahead N]
```

并且没有文件列表，说明工作区干净，只是本地分支领先远端。

### 7.12 推送功能分支

推送当前功能分支：

```bash
git push origin feat/<功能分支>
```

推送后 GitLab MR 会自动更新。

## 8. 常见问题与解决方法

### 8.1 GitLab 看不到本地分支

原因：分支还只在本地，没有推送到远端。

解决：

```bash
git push -u origin <分支名>
```

推送后，GitLab 的 source branch 下拉框才能看到该分支。

### 8.2 已有 open MR，不能再次创建

原因：同一个 source branch 已经有未关闭 MR。

处理：

- 不要重复创建 MR。
- 继续 push 到原分支。
- 原 MR 会自动更新。

### 8.3 MR 出现 merge conflict

原因：

- 源分支和目标分支都改了同一个文件或同一区域。
- GitLab 无法自动判断该保留哪边内容。

处理：

1. 在本地把目标分支最新代码合入功能分支。
2. 手动解决冲突。
3. 验证。
4. commit。
5. push 功能分支。

### 8.4 merge 后 GitLab 看起来多了很多提交

把 `origin/master` merge 到功能分支后，功能分支历史里会出现一个 merge commit。

这个 merge commit 有两个父节点：

- 功能分支原来的提交。
- 最新 `origin/master` 的提交链。

因此 GitLab 的分支提交列表有时会把 `master` 上合进来的提交也显示出来，看起来像“多了很多提交”。

判断 MR 实际多了多少提交，应以目标分支比较为准：

```bash
git rev-list --left-right --count origin/master...feat/<功能分支>
```

例如：

```text
0  4
```

表示相对 `origin/master`，功能分支实际只有 4 个提交。

如果原来有 3 个业务提交，合并 master 后通常会变成：

- 原来的 3 个业务提交。
- 1 个 merge commit。

这是正常现象。

### 8.5 worktree 跑错目录

现象：明明改了功能分支，但页面没变化。

原因：启动项目的目录不是功能分支所在 worktree。

检查：

```bash
git worktree list
git branch --show-current
```

处理：

- 进入正确 worktree 目录。
- 在该目录启动项目。

### 8.6 本地 master 混入多个功能

不推荐在 `master` 上长期开发多个功能。如果已经混入：

1. 先 stash 当前改动。
2. 恢复干净 `master`。
3. 从最新 `master` 新建不同功能分支或 worktree。
4. 从 stash 中按文件恢复到对应功能分支。

示例：

```bash
git stash push -u -m "temp-save-before-splitting-features"
git switch master
git pull origin master
git switch -c feat/feature-a
git checkout stash@{0} -- path/to/feature-a-file
```

### 8.7 stash pop 后又产生冲突

原因：stash 中的改动和当前分支已有改动冲突。

处理：

1. 查看冲突文件。
2. 手动解决冲突。
3. 删除冲突标记。
4. `git add -- <冲突文件>`。
5. 继续提交或保留工作区改动。

常用命令：

```bash
git diff --name-only --diff-filter=U
git status --short --branch
```

### 8.8 commit 被 hook 阻塞

原因可能包括：

- lint 不通过。
- 格式检查不通过。
- 测试不通过。
- 历史代码中已有问题被 hook 扫到。

处理原则：

1. 优先修复本次改动引入的问题。
2. 如果是冲突相关文件，先单独验证冲突相关文件。
3. 如果确认阻塞来自无关历史问题，且本次改动已验证通过，才考虑 `--no-verify`。

谨慎使用：

```bash
git commit --no-verify -m "chore: 合并最新master并解决冲突"
```

### 8.9 git diff 进入分页器

现象：执行 `git diff` 后终端像卡住。

原因：进入了分页器。

退出：

```text
q
```

避免分页：

```bash
git --no-pager diff
git --no-pager diff --cached
```

### 8.10 误用了 git add .

如果不小心全量暂存：

```bash
git restore --staged .
```

然后重新按文件暂存：

```bash
git add <文件1>
git add <文件2>
git --no-pager diff --cached
```

### 8.11 需要撤销工作区修改

只撤销指定文件：

```bash
git restore <文件>
```

注意：这会丢弃该文件未暂存的修改。

如果不确定是否还需要，先 stash：

```bash
git stash push -u -m "backup-before-restore"
```

### 8.12 误提交后想重新整理

如果只是在本地提交，还没有 push，可以根据情况选择：

保留暂存区：

```bash
git reset --soft HEAD^
```

保留工作区但取消暂存：

```bash
git reset --mixed HEAD^
```

不要轻易使用：

```bash
git reset --hard HEAD^
```

`--hard` 会丢弃工作区和暂存区内容，执行前必须确认不需要这些改动。

## 9. 团队检查清单

### 9.1 开发前检查

- [ ] 已确认当前仓库正确。
- [ ] 已确认当前分支正确。
- [ ] 已执行 `git fetch origin` 或 `git pull` 同步最新代码。
- [ ] 本地工作区没有无关未提交改动。
- [ ] 如果使用 worktree，已确认当前目录就是目标分支目录。

### 9.2 提交前检查

- [ ] 已执行 `git status`。
- [ ] 没有默认使用 `git add .` 全量提交。
- [ ] 已按文件或功能点暂存改动。
- [ ] 已执行 `git --no-pager diff --cached` 检查暂存区。
- [ ] commit message 符合规范。
- [ ] 本次提交只包含相关改动。

### 9.3 MR 前检查

- [ ] 功能分支已推送到远端。
- [ ] GitLab 能看到正确 source branch。
- [ ] target branch 选择正确。
- [ ] 本地自测或冒烟测试通过。
- [ ] 如果已有 MR，没有重复新建。

### 9.4 冲突后检查

- [ ] 已确认功能分支合入最新 `origin/master`。
- [ ] 已删除所有冲突标记。
- [ ] `git diff --name-only --diff-filter=U` 没有输出。
- [ ] `git diff --check` 通过。
- [ ] 冲突相关文件已完成必要 lint 或自测。
- [ ] 已提交 merge commit。
- [ ] 已 push 功能分支，让 MR 自动更新。

### 9.5 上线后检查

- [ ] 已确认 release 分支加上 tag。
- [ ] 已将 release 分支合并回 `master`。
- [ ] 已将 `master` 合并回 `development`。
- [ ] 已删除本次 release 对应功能分支。
- [ ] 已删除 release 分支。
- [ ] 如 `bpmax-plugins` 需要手动 tag，已确认 tag 创建完成。

## 10. 常用 SOP 命令汇总

### 10.1 开发新功能

```bash
git switch master
git pull origin master
git switch -c feat/<英文功能名称>
```

### 10.2 提交代码

```bash
git status
git add <文件1>
git add <文件2>
git --no-pager diff --cached
git commit
```

### 10.3 首次推送功能分支

```bash
git push -u origin feat/<英文功能名称>
```

### 10.4 后续推送

```bash
git push
```

### 10.5 同步本地 master

```bash
git fetch origin
git switch master
git merge --ff-only origin/master
```

### 10.6 功能分支合并最新 master

```bash
git switch feat/<英文功能名称>
git fetch origin
git merge origin/master
```

### 10.7 查看并处理冲突

```bash
git diff --name-only --diff-filter=U
git status --short --branch
```

解决文件后：

```bash
git add -- <冲突文件>
git diff --check
git diff --name-only --diff-filter=U
git commit -m "chore: 合并最新master并解决冲突"
git push
```

### 10.8 临时保存未完成改动

```bash
git stash push -u -m "临时说明"
git stash list
git stash pop
```

## 11. 高风险命令提醒

| 命令 | 风险 | 建议 |
| --- | --- | --- |
| `git reset --hard` | 丢弃工作区和暂存区内容 | 执行前先 `git status`，必要时先 stash |
| `git stash clear` | 清空所有 stash，难以恢复 | 优先用 `git stash drop stash@{n}` 删除指定记录 |
| `git push --force` | 覆盖远端历史，可能影响他人 | 公共分支禁止随意使用，必须先沟通 |
| `git branch -D` | 强制删除本地分支 | 确认分支已合并或已不需要 |
| `git commit --no-verify` | 跳过 hook，可能绕过质量检查 | 只在确认阻塞问题非本次引入时谨慎使用 |



<section class="legacy-comments">
  <h2>评论区</h2>
  <div id="twikoo-article_1776429194802" data-twikoo-path="article_1776429194802"></div>
</section>
