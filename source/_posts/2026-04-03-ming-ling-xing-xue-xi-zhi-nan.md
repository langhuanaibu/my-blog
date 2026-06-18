---
title: "命令行学习指南"
date: "2026-04-03"
updated: "2026-04-03"
categories:
  - "技术学习"
old_id: "article_1775182229767"
twikooPath: "article_1775182229767"
---
<h2>命令行学习指南</h2>
## 1. 先建立正确认识

### 1.1 什么是命令行

命令行就是通过输入文本命令来操作电脑、项目和开发工具的方式。  
在这次对话里，主要涉及了 4 类命令行环境：

- CMD
- PowerShell
- Node.js / npm / Yarn / NVM
- Windows 批处理文件（`.bat` / `.cmd`）

### 1.2 命令行里最重要的 4 个概念

#### 当前目录

很多命令都依赖你“现在站在哪个目录”。

```cmd
cd  显示当前所在的目录路径
dir  列出当前目录下的文件和文件夹
```

#### 安装依赖和启动项目不是一回事

```bash
yarn install  读取 package.json，把依赖包下载到 node_modules 文件夹
yarn start  启动项目开发服务器，关闭终端后服务就会停止
```

- `yarn install`：把依赖下载到硬盘，结果会保留下来
- `yarn start`：启动服务，关闭终端后服务就结束

#### 临时效果和永久效果不是一回事

例如：

```powershell
$env:NODE_OPTIONS="--no-experimental-fetch"  设置临时环境变量，关闭终端即失效
```

这类环境变量通常只在当前窗口有效，关掉终端后就没了。

而下面这种命令执行后的结果会保留在硬盘上：

```bash
yarn install  安装的依赖文件会保存在硬盘
git clone <仓库地址>  克隆的项目代码会保存在硬盘
mkdir demo  创建的新文件夹会保存在硬盘
```

#### 一个前台终端通常只能跑一个长期任务

如果一个命令会持续占用终端，例如：

```bash
yarn start  启动前端项目服务，终端会被占用
yarn dev  启动开发环境服务，终端同样被占用
```

那同一个窗口里一般就不能同时前台再跑另一个项目。  
如果你要同时启动多个项目，通常需要多个终端窗口或多个终端标签页。

---

## 2. CMD 入门

### 2.1 查看当前位置和切换目录

```cmd
cd  显示当前路径
cd src  进入名为 src 的子目录
cd ..  返回上一级目录
cd ../..  返回上两级目录
cd ..\..\..  返回上三级目录（Windows 使用反斜杠也可）
cd \  直接返回当前盘符的根目录
cd /d D:\project\my-app  跨盘符直接切换到指定目录
```

说明：

- `cd`：显示当前路径
- `cd src`：进入子目录
- `cd ..`：回到上一级
- `cd \`：回到当前盘符根目录
- `cd /d D:\project\my-app`：跨盘符切换目录

### 2.2 跨盘符切换

```cmd
D:  切换到 D 盘
cd D:\project\my-app  在 D 盘内切换到具体目录
```

或者一步完成：

```cmd
cd /d D:\project\my-app  /d 参数允许同时切换盘符和路径
```

### 2.3 查看当前目录下有什么

```cmd
dir  列出当前目录下的文件和文件夹详情
dir /b  仅列出文件和文件夹的名称（精简模式）
dir /w  宽格式按列显示内容
dir /s  包含所有子目录中的文件（递归显示）
dir /a  显示所有文件，包含隐藏文件
dir /ad  仅显示文件夹（目录）
dir /a-d  仅显示文件，不显示文件夹
dir /p  列表太长时，满屏后暂停等待按键
dir /o  按名称首字母排序显示
dir > filelist.txt  将 dir 的输出结果保存到 filelist.txt 文件中
tree  以树状图显示当前目录结构
tree /f  以树状图显示目录结构，并包含文件名
```

常见用法：

- `dir`：普通列表
- `dir /b`：只看名称
- `dir /ad`：只看文件夹
- `dir /a-d`：只看文件
- `tree /f`：看目录树和文件
- `dir > filelist.txt`：保存结果到文件

### 2.4 常用辅助命令

```cmd
cls  清除当前终端窗口的屏幕内容
doskey /history  显示当前窗口输入过的命令历史记录
echo %cd%  打印当前所在的目录路径
cd %USERPROFILE%  切换到当前 Windows 用户的个人主目录（如 C:\Users\xxx）
cd %USERPROFILE%\Desktop  切换到当前用户的桌面目录
```

### 2.5 带空格目录的处理

```cmd
cd "Program Files"  目录名有空格时，必须用双引号包起来
cd progra~1  使用 Windows 的 8.3 短文件名格式（较老旧的做法）
```

学习建议：路径里有空格时，优先用双引号包住。

---

## 3. PowerShell 常用命令

PowerShell 比 CMD 更强，尤其擅长筛选、批量处理和对象管道。

### 3.1 文件与目录

```powershell
Get-ChildItem  列出当前目录的内容（等同于 dir / ls）
ls  Get-ChildItem 的常用简写
ls -Recurse  递归列出所有子目录及内容
Set-Location D:\project  切换目录到 D:\project
cd D:\project  Set-Location 的常用简写
sl D:\project  Set-Location 的另一种简写
Get-Location  获取当前路径
pwd  Get-Location 的常用简写
New-Item demo.txt  创建一个空文件 demo.txt
New-Item demo -ItemType Directory  创建一个名为 demo 的文件夹
Remove-Item demo.txt  删除 demo.txt 文件
Remove-Item demo -Recurse  递归删除 demo 文件夹及其所有内容
Copy-Item a.txt b.txt  将 a.txt 复制为 b.txt
Move-Item a.txt D:\  将 a.txt 移动到 D 盘根目录
Rename-Item a.txt b.txt  将 a.txt 重命名为 b.txt
```

### 3.2 查看和处理文件内容

```powershell
Get-Content package.json  在终端中打印 package.json 的全部内容
cat package.json  Get-Content 的常用简写
type package.json  也是 Get-Content 的简写
Set-Content output.txt "hello"  将 "hello" 覆盖写入 output.txt
Add-Content output.txt "world"  将 "world" 追加到 output.txt 末尾
Select-String "error" *.log  在所有 log 文件中搜索包含 "error" 的行
ls | Out-File list.txt  将 ls 的输出结果保存到 list.txt 文件中
```

### 3.3 进程与服务

```powershell
Get-Process  列出当前正在运行的所有进程
ps  Get-Process 的简写
ps node  仅列出名为 node 的进程
Stop-Process -Id 1234  停止进程 ID 为 1234 的进程
Stop-Process -Id 1234 -Force  强制停止进程 ID 为 1234 的进程
kill -Name node  强制停止所有名为 node 的进程
kill -Id 1234  强制停止进程 ID 为 1234 的进程
Start-Process notepad.exe  启动记事本程序
Get-Service  列出系统所有的服务状态
Get-Service *mysql*  列出名字中包含 mysql 的服务
Stop-Service Spooler  停止打印后台处理服务（Spooler）
Start-Service Spooler  启动打印后台处理服务
```

### 3.4 网络与系统信息

```powershell
Test-Connection google.com  测试是否能 ping 通 google.com
Invoke-WebRequest -Uri "https://example.com/file.zip" -OutFile file.zip  从网络下载文件
Test-NetConnection google.com -Port 443  测试能否连接到 google.com 的 443 端口
Get-NetIPAddress  查看本机的 IP 地址信息
Get-Date  获取当前系统日期和时间
Get-History  获取当前 PowerShell 窗口的命令输入历史
Clear-Host  清屏
cls  Clear-Host 的简写
exit  退出当前 PowerShell 窗口
```

### 3.5 环境变量

```powershell
Get-ChildItem Env:  查看系统中所有的环境变量
$env:PATH  打印系统的 PATH 环境变量内容
$env:NODE_ENV="production"  临时设置 NODE_ENV 变量为 production
Get-Command node  查找 node 命令的实际可执行文件路径
```

临时设置与撤销：

```powershell
$env:NODE_OPTIONS="--no-experimental-fetch"  临时设置 NODE_OPTIONS
$env:NODE_OPTIONS  查看 NODE_OPTIONS 的当前值
$env:NODE_OPTIONS=""  将 NODE_OPTIONS 清空，相当于撤销设置
```

### 3.6 PowerShell 最值得学的能力：管道

```powershell
Get-Process | Where-Object { $_.ProcessName -like "*node*" }  筛选出名字包含 node 的进程
ps | where { $_.Name -like "*node*" }  上一条命令的简写版
ls | Select-Object Name, Length  列出文件，但只保留名称和大小属性
ls | Sort-Object Length -Descending  列出文件并按大小从大到小排序
cat log.txt | Measure-Object -Line  统计 log.txt 文件的总行数
cat app.log | Select-String "error"  读取日志并筛选出包含 error 的行
```

理解方式：

- `|` 前面产出结果
- `|` 后面继续筛选、排序、统计

### 3.7 帮助、别名与命令发现

```powershell
Get-Help ls  查看 ls 命令的官方帮助文档
Get-Help ls -Examples  直接查看 ls 命令的用法示例
Get-Command  列出所有可用的命令
Get-Command *process*  查找名称中包含 process 的命令
Get-Alias  列出所有命令的简写别名
Get-Alias ls  查看 ls 是哪个命令的别名（指向 Get-ChildItem）
Get-ExecutionPolicy  查看当前 PowerShell 的脚本执行策略
Set-ExecutionPolicy RemoteSigned  设置允许运行本地编写的脚本
```

---

## 4. Git：把项目拉到本地

这次对话里最核心的 Git 命令是：

```bash
git clone <仓库地址>  将远程仓库的代码完整下载到本地文件夹
```

作用：

- 把远程仓库完整复制到本地

常见流程：

```bash
git clone <仓库地址>  克隆项目代码到本地
cd 项目目录  进入刚克隆出来的项目文件夹
```

如果仓库是私有的，通常还需要提前准备权限，例如：

- 登录对应平台
- 配置 SSH
- 或使用 Token

---

## 5. Yarn：项目依赖与脚本管理

### 5.1 Yarn 是干什么的

Yarn 是 JavaScript 包管理工具，主要做 3 件事：

- 安装依赖
- 管理依赖版本
- 运行项目脚本

### 5.2 安装 Yarn

```bash
npm install -g yarn  使用 npm 将 Yarn 安装到全局环境
yarn --version  查看已安装的 Yarn 版本号
yarn -v  yarn --version 的简写
```

### 5.3 安装项目依赖

```bash
yarn  安装 package.json 中列出的所有依赖
yarn install  明确写出 install，功能和直接输入 yarn 一样
yarn install --immutable  严格按照锁文件安装，不允许修改锁文件
yarn install --frozen-lockfile  锁文件不匹配时直接报错，常用于 CI/CD
yarn install --verbose  安装时输出极为详细的日志信息，用于排错
```

说明：

- `yarn` 和 `yarn install` 常常等价
- `--frozen-lockfile`：更严格地按锁文件安装
- `--immutable`：在部分 Yarn 版本/工作区场景中使用
- `--verbose`：看更详细日志

### 5.4 添加、删除、更新依赖

```bash
yarn add <package-name>  将包安装并记录到 dependencies (生产依赖)
yarn add -D <package-name>  将包安装并记录到 devDependencies (开发依赖)
yarn add -O <package-name>  将包安装并记录到 optionalDependencies (可选依赖)
yarn add <package>@<version>  安装某个包的指定版本
yarn remove <package-name>  卸载包并从 package.json 中移除记录
yarn upgrade  按照 package.json 的版本范围升级所有包
yarn upgrade <package-name>  仅升级指定的包
yarn upgrade-interactive  提供一个交互式界面让你勾选要升级的包
yarn upgrade-interactive --latest  交互式升级，且允许跨越主版本号升到最新
yarn outdated  检查并列出哪些包有新版本可更新
```

### 5.5 查看依赖信息

```bash
yarn list  树状打印当前项目安装的所有依赖
yarn list --depth=0  仅打印第一层直接依赖，不展开子依赖
yarn why <package>  查询解释为什么当前项目里会安装这个包
yarn info <package>  查看某个包在远程仓库中的版本、协议等详细信息
yarn cache clean  清理 Yarn 下载在本地的全局缓存包
yarn cache list  列出当前 Yarn 缓存的所有包
```

### 5.6 初始化项目

```bash
yarn init  通过一问一答的方式创建一个新的 package.json
yarn init -y  跳过所有提问，直接使用默认值创建 package.json
```

### 5.7 运行项目脚本

```bash
yarn run  列出 package.json 里定义的所有可用脚本
yarn start  运行名为 start 的脚本（通常用于启动项目）
yarn dev  运行名为 dev 的脚本（通常用于本地开发）
yarn serve  运行名为 serve 的脚本（通常用于启动本地服务器）
yarn start:dev  运行自定义名字的 start:dev 脚本
yarn start:local  运行自定义名字的 start:local 脚本
yarn start:win-local  运行自定义名字的 start:win-local 脚本
yarn start-win-local  运行自定义名字的 start-win-local 脚本
```

理解方式：

- `yarn run`：列出或运行脚本
- `yarn start`、`yarn dev`：是否可用，取决于 `package.json` 的 `scripts`

### 5.8 查看项目有哪些脚本

Windows 常见写法：

```cmd
type package.json | findstr "scripts"  在 package.json 中过滤出包含 scripts 的行
type package.json | findstr "start-win-local"  查找特定启动脚本的配置详情
notepad package.json  直接用记事本打开 package.json 查看
```

类 Unix 风格写法：

```bash
cat package.json | grep "scripts" -A 10  找到 scripts 所在行，并往下多看 10 行
cat package.json | findstr "start:win-local"  跨平台终端里用 findstr 查找（混用示例）
```

更直接的方式：

```bash
yarn run  直接让 Yarn 列出所有可执行的脚本清单
```

### 5.9 Yarn 与 npm 的常见对照

| 目的 | Yarn | npm |
|---|---|---|
| 安装所有依赖 | `yarn install` | `npm install` |
| 添加依赖 | `yarn add axios` | `npm install axios` |
| 删除依赖 | `yarn remove axios` | `npm uninstall axios` |
| 运行脚本 | `yarn start` | `npm start` / `npm run start` |

### 5.10 什么时候要重新执行 Yarn

#### 关闭终端后

- 不需要重新执行 `yarn install`
- 需要重新执行 `yarn start` 或 `yarn dev`

#### 什么时候才需要重新安装依赖

- 第一次拿到项目
- `package.json` 或锁文件变了
- 依赖损坏需要重装

---

## 6. Yarn Link：本地包联调

### 6.1 建立链接

```bash
yarn link  在本地包目录下执行，将其注册到全局 link 列表
yarn link <package-name>  在使用方项目中执行，将包软链接过来
```

### 6.2 取消链接

```bash
yarn unlink  在本地包目录下执行，将其从全局 link 列表移除
yarn unlink <package-name>  在使用方项目中执行，断开软链接
yarn add <package-name> --force  强制重新下载并覆盖，清除可能残留的链接状态
```

### 6.3 查看与排查

```bash
yarn link list  列出当前项目建立的所有软链接
yarn config get nmLink  查看 Yarn 关于 link 的底层配置机制
ls -la node_modules/<package-name>  查看该模块是否是一个指向其他路径的快捷方式
```

### 6.4 关闭终端后会怎样

学习时可以先这样记：

- 全局注册这一步通常保留
- 使用方项目里的联调关系、启动进程经常需要重新处理
- 如果你长期本地联调，`file:` 依赖或 monorepo/workspaces 往往更省心

---

## 7. Node.js 与 NVM

### 7.1 为什么学 NVM

NVM 用来管理多个 Node.js 版本。  
典型场景：

- 这个项目要 Node 16
- 另一个项目要 Node 18
- 你不想每次卸载重装 Node

### 7.2 安装指定版本、最新版、LTS 版

```bash
nvm install 16  安装 Node 16 的最新小版本
nvm install 16.20.2  精确安装 Node 16.20.2 版本
nvm install latest  安装当前 Node.js 的最新版
nvm install lts  安装当前 Node.js 的长期维护版
nvm install node  (类 Unix 系统下) 安装最新的 Node.js
nvm install --lts  (类 Unix 系统下) 安装 LTS 版本的 Node.js
```

说明：

- Windows 对话里提到：`nvm install latest`
- macOS / Linux 对话里提到：`nvm install node`
- `nvm install 16` 适合快速装主版本
- `nvm install 16.20.2` 适合精确版本

### 7.3 切换版本

```bash
nvm use 16  切换当前使用的 Node 版本为 16.x
nvm use latest  切换到已安装的最新版本
nvm use node  (类 Unix 系统下) 切换到默认/最新版本
```

### 7.4 查看当前状态

```bash
nvm ls  列出本地已安装的所有 Node 版本
nvm list  nvm ls 的另一种写法
nvm list available  (Windows下) 列出网络上可供下载的 Node 版本列表
nvm ls-remote  (类 Unix系统下) 列出网络上可供下载的版本列表
nvm current  显示当前正在使用的 Node 版本号
nvm version  查看 nvm 工具自身的版本号
nvm -v  nvm version 的简写
nvm arch  查看 Node 运行在 32 位还是 64 位架构下
```

### 7.5 设置默认版本、卸载版本

```bash
nvm alias default 16  设置打开新终端时默认使用的版本为 16
nvm alias default <版本号>  设置默认版本为指定版本
nvm uninstall 16  卸载 Node 16 版本
nvm uninstall <版本号>  卸载指定的 Node 版本
```

### 7.6 其他常见命令

```bash
nvm on  启用 nvm 的版本管理接管功能
nvm off  停用 nvm，恢复系统原本的 Node 路径
nvm reinstall-packages  重装 npm 全局包到新切换的版本中
nvm run <version> <script>  不切换环境的情况下，临时用指定版本执行脚本
```

### 7.7 验证 Node 和 npm 是否正常

```bash
node -v  打印当前使用的 Node 版本号
npm -v  打印当前使用的 npm 版本号
npm config get prefix  查看 npm 全局包的安装位置
```

### 7.8 其他安装方式（对话里提到过）

Windows（直接安装系统级 Node 16）：

```powershell
winget install OpenJS.NodeJS.16  使用 Windows 包管理器安装 Node 16
```

macOS / Linux（安装 nvm 的脚本方式）：

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.3/install.sh | bash  用 curl 下载并执行 nvm 安装脚本
wget -qO- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.3/install.sh | bash  用 wget 下载并执行 nvm 安装脚本
```

Linux（Debian/Ubuntu 用 NodeSource 仓库安装 Node 16）：

```bash
curl -fsSL https://deb.nodesource.com/setup_16.x | sudo -E bash -  添加 NodeSource 的源配置
sudo apt install -y nodejs  使用 apt 最终安装 nodejs
```

---

## 8. 环境变量与跨平台写法

### 8.1 同一个意思，不同终端写法不同

设置 `NODE_OPTIONS` 的写法：

CMD：

```cmd
set NODE_OPTIONS=--no-experimental-fetch  在 CMD 中临时设置环境变量
```

PowerShell：

```powershell
$env:NODE_OPTIONS="--no-experimental-fetch"  在 PowerShell 中临时设置环境变量
```

macOS / Linux：

```bash
export NODE_OPTIONS="--no-experimental-fetch"  在 Bash/Zsh 中临时设置环境变量
```

### 8.2 撤销临时环境变量

PowerShell：

```powershell
$env:NODE_OPTIONS=""  将变量赋空，等同于撤销
$env:NODE_OPTIONS  打印该变量验证是否已清空
```

### 8.3 为什么 `yarn start --no-experimental-fetch` 会报错

因为这个参数是给 `node` 的，不是给 `yarn` 的。  
正确思路是先设置环境变量，再执行启动命令。

```powershell
$env:NODE_OPTIONS="--no-experimental-fetch"  先设置环境变量
yarn start  然后再启动项目，项目里的 Node 就能读到上面的配置
```

### 8.4 Shell 配置相关命令

```bash
echo $SHELL  查看当前使用的默认 Shell 类型（如 bash 还是 zsh）
nano ~/.zshrc  用终端文本编辑器 nano 修改 zsh 配置文件
source ~/.zshrc  让刚才修改的 zsh 配置文件立刻生效
source ~/.bashrc  让修改后的 bash 配置文件立刻生效
```

---

## 9. 运行文件与脚本

### 9.1 运行当前目录下的程序

```powershell
.\node_modules\.bin\webpack  运行当前目录下相对路径里的 webpack 命令
.\script.ps1  运行当前目录下的 PowerShell 脚本
.\build.bat  运行当前目录下的 CMD 批处理脚本
```

在 PowerShell 中，当前目录下的文件通常要写 `.\`。

### 9.2 运行指定路径程序

```powershell
D:\tools\ffmpeg.exe -version  直接调用 D 盘绝对路径下的 exe 程序
```

### 9.3 运行常见脚本文件

```powershell
python .\app.py  用 Python 解释器执行 app.py 脚本
python app.py  同上，省略了 .\
node .\index.js  用 Node.js 执行 index.js 脚本
node index.js  同上，省略了 .\
PowerShell -NoExit -File ".\myscript.ps1"  新开一个 PowerShell 跑脚本，跑完不退出窗口
msiexec /i .\installer.msi  调用 Windows 安装程序静默或显式安装 msi 包
```

### 9.4 在 PATH 里的程序可以直接运行

```powershell
node --version  由于 node 在系统环境变量 PATH 里，随处都可直接敲
npm install  npm 也在 PATH 里，直接敲即可
git status  git 也在 PATH 里，直接敲即可
```

---

## 10. 端口、进程、排错

### 10.1 查看端口是否被占用

```powershell
netstat -ano | findstr :3000  查找占用 3000 端口的网络连接及进程 PID
netstat -ano | findstr :%port%  查找指定端口的占用情况（%port% 需替换为数字）
Get-NetTCPConnection -LocalPort 3000  PowerShell 原生查 3000 端口占用的命令
```

### 10.2 结束占用端口的进程

```powershell
Stop-Process -Id 1234 -Force  强制干掉进程 ID 为 1234 的进程
kill -Id 1234  Stop-Process 的简写版
kill -Name node  强制干掉所有名字叫 node 的进程
```

### 10.3 检查网络连通

```powershell
Test-Connection google.com  类似 ping，测试能否连接对方服务器
Test-NetConnection google.com -Port 443  高级测试，明确测对方的 443 端口通不通
Get-NetIPAddress  查自己电脑分配到了什么 IP
```

---

## 11. 批处理文件基础

### 11.1 最常见的开头

```batch
@echo off  告诉终端：后面的所有命令本身不要打印出来，只打印命令的结果
```

作用：关闭后续命令回显，让输出更干净。

### 11.2 注释

```batch
REM 这是注释（标准注释写法示例）  使用 REM 关键字作为官方注释
:: 这也是注释（常见的“标签式”注释写法示例）  冒号开头本是标签，常被借用当注释
@REM 这也是注释（示例：@ 表示本行不回显）  确保即使没有 echo off，这行注释也不会打印
```

### 11.3 输出、暂停、退出

```batch
echo Hello  在屏幕上打印出 Hello 文字
echo.  打印一个空行
pause  暂停脚本执行，提示“请按任意键继续...”
exit /b 0  退出当前脚本并返回成功状态码 0
```

### 11.4 变量

```batch
set name=John  定义一个名为 name 的变量，值为 John
echo %name%  打印变量 name 的值
set /a num=5+3  进行数学计算，num 被赋值为 8
set /p input=请输入内容：  暂停并在屏幕提示，将用户的输入赋值给 input 变量
```

### 11.5 参数

```batch
echo %0  打印脚本本身的名字或路径
echo %1  打印运行脚本时传进来的第 1 个参数
echo %2  打印运行脚本时传进来的第 2 个参数
echo %*  打印运行脚本时传进来的所有参数
```

### 11.6 条件判断

```batch
if "%name%"=="John" (  判断 name 变量的值是否等于 John
    echo yes  条件成立时打印 yes
) else (  否则
    echo no  条件不成立时打印 no
)

if exist "C:\test.txt" (  判断指定路径的文件存不存在
    echo exist  存在则打印 exist
)

if defined name (  判断 name 这个变量有没有被声明过
    echo defined  如果定义过则打印 defined
)
```

常见比较符：

- `EQU`
- `NEQ`
- `LSS`
- `LEQ`
- `GTR`
- `GEQ`

### 11.7 循环

```batch
for %%f in (*.txt) do (  遍历当前目录下所有后缀为 .txt 的文件
    echo %%f  打印出找到的文件名
)

for /l %%i in (1,1,10) do (  计数循环，从 1 开始，每次加 1，直到 10
    echo %%i  打印当前数字
)

for /d %%d in (*) do (  遍历当前目录下所有的文件夹
    echo %%d  打印文件夹名
)

for /f "tokens=*" %%l in (file.txt) do (  逐行读取 file.txt 的文本内容
    echo %%l  打印读到的每一行
)
```

### 11.8 跳转

```batch
goto :label1  命令跳到 :label1 标记处继续执行

:label1  定义一个名为 label1 的跳转标记
echo hello  打印 hello
goto :end  跳到结尾处

:end  定义一个名为 end 的标记
echo done  打印 done
```

### 11.9 调用其他脚本和等待

```batch
call other.bat  在当前脚本里调用另一个批处理，等它执行完再回来
timeout /t 5 /nobreak  倒计时 5 秒，且不允许用户按键跳过
start notepad.exe  启动记事本，不等待记事本关闭，脚本继续往下走
```

### 11.10 错误处理与静默输出

```batch
copy file.txt D:\  尝试复制文件
if %errorlevel% equ 0 (  检查上一条复制命令的返回码是否为 0（代表成功）
    echo success  成功则打印
) else (  否则
    echo fail  失败则打印
)

copy file.txt D:\ && echo success || echo fail  简写逻辑：成功打印 success，失败打印 fail
dir nonexistent 2>nul  查不存在的文件时，把报错信息扔进黑洞不显示
command >nul 2>&1  将命令的正常输出和报错输出全部隐藏
```

### 11.11 编码、标题、颜色、延迟变量

```batch
chcp 65001 >nul  将终端字符编码改为 UTF-8 以防中文乱码，且不打印提示
title 我的脚本  将终端窗口的左上角标题改成“我的脚本”
color 0a  改变终端字体颜色（0a 代表黑底亮绿字，黑客帝国风）
setlocal enabledelayedexpansion  开启变量延迟扩展（解决在 for/if 块中变量不更新的坑）
```

### 11.12 常见路径技巧

- `%~dp0`
- `%~d0`
- `%~p0`

---

## 12. 批处理里的文件操作

```batch
md newfolder  创建一个名为 newfolder 的文件夹
mkdir new_folder  也是创建文件夹
rd /s /q folder  递归删除 folder 文件夹，不弹出确认提示
rmdir /s /q folder  和 rd 功能一样
del *.txt  删除当前目录下所有 txt 文件
del /f /q "%temp%\*.*" 2>nul  强制、静默清理系统临时文件夹，忽略报错
copy a.txt b.txt  复制文件
copy config.ini backup_config.ini  备份配置文件
move a.txt D:\  移动文件
ren a.txt b.txt  重命名文件
```

对话里也出现了下面这种“清理并重装依赖”的思路：

```bash
rm -rf node_modules  强制递归删除 node_modules 文件夹（Linux/macOS 写法）
rm -rf node_modules yarn.lock  一次性强制删除文件夹和锁文件
yarn install  重新安装纯净的依赖
```

说明：这是类 Unix 风格的删除写法，在纯 Windows CMD 里不能直接照抄。

---

## 13. Redis 命令行基础

对话里还提到了 Redis 的一些入门命令：

```bash
redis-cli set username "zhangsan"  连接 Redis 并存入一个 key 为 username 的数据
redis-cli get username  从 Redis 中取出 username 的值
redis-cli hset user:1001 name "zhangsan" age 25  以哈希结构存入用户数据
redis-cli hget user:1001 name  从哈希结构中查出用户的 name
redis-cli -h <host> -p <port>  指定 IP 和端口连接到远程 Redis 数据库
keys *  在 Redis 控制台内，列出所有的 key
get some_key  在 Redis 控制台内，获取某个 key 的值
incr article:123:likes  在 Redis 控制台内，给文章点赞数自增 1
```

可以把它理解成：

- `set/get`：最基础的键值读写
- `hset/hget`：操作哈希
- `incr`：计数器自增

---

## 14. 多项目同时启动的理解

如果一个文件夹下有多个项目，例如前端和后端，那么通常要这样做：

```bash
cd frontend  进入前端文件夹
yarn dev  启动前端开发服务
```

再开一个新终端：

```bash
cd backend  进入后端文件夹
yarn start  启动后端服务
```

原因是：

- `yarn dev`
- `yarn start`

这类命令大多会持续占用当前终端。

---

## 15. 关闭终端后哪些还有效

### 15.1 通常还有效

- `git clone`
- `yarn install`
- `mkdir`
- `copy`

因为这些命令把结果写进了硬盘。

### 15.2 通常会失效

- `yarn start`
- `yarn dev`
- 临时环境变量
- 当前窗口里运行的批处理进程

因为这些依赖当前终端会话或当前运行中的进程。

---

## 16. 建议你优先掌握的命令

如果你是从零开始学命令行，建议按这个顺序练：

### 第 1 组：目录与文件

```cmd
cd  查路径
cd ..  回上级
cd /d D:\project  切盘符进项目
dir  看文件
dir /b  精简看文件
tree /f  看目录树
cls  清屏
```

### 第 2 组：项目启动

```bash
git clone <仓库地址>  下载代码
cd 项目目录  进代码目录
yarn install  装依赖
yarn start  跑服务
yarn run  看脚本
```

### 第 3 组：Node 版本管理

```bash
nvm install 16  装指定版本
nvm use 16  切换版本
node -v  检查 node 生效没
npm -v  检查 npm 生效没
```

### 第 4 组：排错

```powershell
netstat -ano | findstr :3000  查端口谁占了
Get-NetTCPConnection -LocalPort 3000  也是查端口
Stop-Process -Id 1234 -Force  强杀进程
$env:NODE_OPTIONS=""  清空异常环境变量
```

### 第 5 组：批处理自动化

```batch
@echo off  关回显
set name=demo  设变量
if exist "a.txt" echo yes  判断文件存在
for %%f in (*.txt) do echo %%f  循环遍历
pause  暂停看结果
```

---

## 17. 最后给你的学习结论

你可以把这次对话里出现的命令行知识总结成下面这几句话：

1. 命令行最先学的是“目录”和“当前路径”。
2. 项目开发最常见的是 `git clone`、`yarn install`、`yarn start`。
3. Node 版本不对时，优先想到 `nvm install` 和 `nvm use`。
4. 服务起不来时，优先检查脚本、环境变量、端口占用。
5. 批处理适合把重复步骤写成脚本自动执行。
6. 关闭终端后，长期运行的服务会停，但写进硬盘的结果会保留。

## 附录：命令行核心速查表

### 1. 目录与基础操作
| 目标 | Windows CMD | PowerShell | macOS / Linux |
|---|---|---|---|
| 查看当前路径 | `cd` | `pwd` 或 `Get-Location` | `pwd` |
| 进入目录 | `cd folder` | `cd folder` | `cd folder` |
| 返回上一级 | `cd ..` | `cd ..` | `cd ..` |
| 跨盘符切换 | `cd /d D:\folder` | `cd D:\folder` | 不适用 |
| 列出文件 | `dir` | `ls` 或 `Get-ChildItem` | `ls` |
| 清屏 | `cls` | `cls` 或 `Clear-Host` | `clear` |

### 2. Node 与 NVM (版本管理)
| 命令 | 作用说明 |
|---|---|
| `node -v` | 验证并查看当前 Node.js 版本 |
| `npm -v` | 验证并查看当前 npm 版本 |
| `nvm ls` | 查看本地已安装的所有 Node 版本 |
| `nvm install 16` | 安装 Node.js 16 版本 |
| `nvm use 16` | 切换并使用 Node.js 16 版本 |
| `nvm alias default 16` | 设置默认启动使用的版本为 16 |

### 3. Yarn (包管理与脚本)
| 命令 | 作用说明 | 等效的 npm 命令 |
|---|---|---|
| `yarn install` 或 `yarn` | 根据 package.json 安装所有依赖 | `npm install` |
| `yarn add <pkg>` | 安装并添加某个依赖到生产环境 | `npm install <pkg>` |
| `yarn start` | 启动项目服务 (依赖 package.json scripts) | `npm start` |
| `yarn dev` | 启动开发服务 | `npm run dev` |
| `yarn run` | 列出当前项目有哪些脚本可以运行 | `npm run` |
| `yarn cache clean` | 清理 Yarn 本地缓存 | `npm cache clean --force` |

### 4. 环境变量 (临时设置)
| 终端类型 | 设置语法示例 | 撤销/清空示例 |
|---|---|---|
| Windows CMD | `set NODE_OPTIONS=--abc` | `set NODE_OPTIONS=` |
| PowerShell | `$env:NODE_OPTIONS="--abc"` | `$env:NODE_OPTIONS=""` |
| macOS / Linux | `export NODE_OPTIONS="--abc"` | `unset NODE_OPTIONS` |

### 5. 端口与排错
| 目标 | Windows PowerShell |
|---|---|
| 查 3000 端口被谁占用 | `netstat -ano \| findstr :3000` |
| 强制结束指定 ID 进程 | `kill -Id 1234` 或 `Stop-Process -Id 1234 -Force` |
| 强制结束名为 node 进程 | `kill -Name node` |
| 测试网络能否连通 | `Test-Connection google.com` |


<section class="legacy-comments">
  <h2>评论区</h2>
  <div id="twikoo-article_1775182229767" data-twikoo-path="article_1775182229767"></div>
</section>
