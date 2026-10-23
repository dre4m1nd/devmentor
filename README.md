# DevMentor · 编程导师终端智能体

终端里的编程导师。它不只回答问题——任何"这段能跑"的说法，都会**先用 javac 真编译、真运行一遍**再讲。

在终端敲一行就能开始：

```
$ devmentor
```

---

## 它做什么

| 能力 | 说明 |
| --- | --- |
| 代码真跑验证 | 用 JDK 编译并运行你贴的 Java 代码，返回退出码 / stdout / stderr |
| 编译诊断 | 只编译不运行，给出 行:列 级别的报错 |
| 跨会话记忆 | 学到哪、聊过什么，重启后上下文还在 |
| 6 个模型厂商 | OpenRouter / DeepSeek / DashScope / OpenAI / Anthropic / 本地 Ollama |

**不想注册任何服务也能用**：`/login` 选第 6 项 Ollama，本地模型不要 Key。

---

## 目录说明

| 目录 | 说明 |
| --- | --- |
| `backend/` | Python agent 服务（核心） |
| `frontend/` | Node + Ink 终端 UI |

---

## 架构

前后端分离，通过 **JSON-lines over stdio** 通信：

```
┌──────────────────────────────┐
│  frontend/  (Node + Ink)     │
│  · React 组件渲染            │
│  · 输入与命令补全            │
│  · 不碰业务逻辑              │
└──────────────┬───────────────┘
               │  stdin/stdout  每行一个 JSON
┌──────────────┴───────────────┐
│  backend/   (Python)         │
│  · AgentScope Agent          │
│  · 2 个工具（都用来跑代码）  │
└──────────────────────────────┘
```

**为什么这么分**：前端只做渲染，后端只做推理与工具。改 UI 不用碰 Agent，换模型不用碰 UI。

---

## 安装

### 前置条件

- **Python 3.11+**
- **Node.js 18+**
- **JDK 17+**（必须是 JDK 不是 JRE——导师要用 javac 跑代码）

### 步骤

一条命令装完依赖、构建前端、挂上全局 `devmentor`：

```bash
git clone https://github.com/dre4m1nd/devmentor.git
cd devmentor

# Windows
powershell -ExecutionPolicy Bypass -File install.ps1

# macOS / Linux
bash install.sh
```

装完**新开一个终端**，然后：

```bash
devmentor          # 直接启动，像 claude 一样
```

脚本做了四件事：

1. 检查 Python 3.11+、Node.js 18+、JDK 17+
2. `pip install -e backend/` 装齐依赖
3. 构建前端（`npm install && npm run build`）
4. 写启动脚本到 `~/.devmentor/bin/devmentor` 并加入 PATH

启动脚本指向**本仓库**的 `frontend/dist/cli.js`，因此 `git pull` 更新代码后
重新跑一次安装脚本即可。想换机器位置就设 `DEVMENTOR_PROJECT_ROOT`。

#### 卸载

```bash
rm -rf ~/.devmentor                    # macOS / Linux
# Windows: Remove-Item -Recurse $env:USERPROFILE\.devmentor
```

再从「系统属性 → 环境变量」里删掉 PATH 中的 `%USERPROFILE%\.devmentor\bin`。

#### 手动安装（不用脚本）

```bash
git clone https://github.com/dre4m1nd/devmentor.git
cd devmentor
cd backend && pip install -e . && cd ..
cd frontend && npm install && npm run build && cd ..
node frontend/dist/cli.js
```

依赖只有一个：`agentscope`。装完可以自查：

```bash
cd backend && python -c "import agentscope; print(agentscope.__version__)"
```

---

## 第一次对话：登录模型

启动后 banner 会告诉你当前凭据状态：

```
  模型     openai:minimax/minimax-m3.1-flash:free
  凭据     未登录 — 输入 /login 选择厂商并填入 API Key
```

输入 `/login`，选厂商、粘贴 Key。**不想注册任何服务**时选第 6 项 Ollama，本地模型不要 Key。

Key 的存储与优先级：

- 位置 `~/.devmentor/credentials`（不在项目里，不会误提交），POSIX 下 0600
- 优先级：**环境变量 > 本地凭据文件**——CI 里注入的 Key 会盖掉你本机的个人 Key
- 换 Key：再执行 `/login`；清除：`/logout`

---

## 用法

### 命令补全

输入 `/` 立刻弹出候选，**↑ ↓ 选择**、**Tab 或 Enter 确认**。

### 斜杠命令

| 命令 | 作用 |
| --- | --- |
| `/login` / `/logout [厂商]` | 登录厂商 / 清除凭据 |
| `/new [名字]` / `/reset` | 开新会话 / 清空当前上下文 |
| `/mode <interactive read-only full>` | 切换权限档位（见下） |
| `/model [id]` | 查看或切换模型 |
| `/session` / `/workspace` / `/tools` | 查看会话 / 工作区 / 工具清单 |
| `/quit` | 退出 |

### 权限档位（真的生效）

三档在工具层面产生不同的 `PermissionDecision`，不是只改提示文案：

| 档位 | 写类工具（java_run_snippet） | 只读工具 |
| --- | --- | --- |
| `interactive`（默认） | **ASK** —— 执行前必须确认，且 bypass-immune | 直接放行 |
| `read-only` | **DENY** —— 直接拒绝，模型会收到原因并换方案 | 直接放行 |
| `full` | **ALLOW** —— 不再询问（谨慎） | 直接放行 |

> **能力边界**：代码真跑验证只支持 Java。导师讲解 Python、JS 等其它语言没有问题，
> 但它会明确说"这段我没有执行过"，不会把没跑过的代码说成已验证。

---

## 项目结构

```
devmentor/
├── backend/                      Python agent 服务
│   ├── devmentor/
│   │   ├── protocol.py           前后端协议（唯一契约）
│   │   ├── server.py             JSON-lines 主循环
│   │   ├── service.py            AgentScope 事件 -> 协议事件
│   │   ├── agent.py              Agent 装配
│   │   ├── commands.py           斜杠命令
│   │   ├── config.py             厂商目录、凭据、JDK 查找
│   │   ├── workspace.py          工作区模板落盘
│   │   └── tools/                java_run_snippet / java_compile_check
│   └── tests/                    测试
└── frontend/                     Ink 终端 UI
    └── src/
        ├── types.ts              协议类型
        ├── backend.ts            子进程管理与 JSON 行读写
        ├── commands.ts           命令表与补全数据
        └── components/           Banner / EntryView / ConfirmBox / Prompt / App
```

---

## 配置

全部配置走环境变量，改完重启生效。

| 环境变量 | 默认值 | 作用 |
| --- | --- | --- |
| `DEVELOPMENT_MODEL_ID` | `openai:minimax/minimax-m3.1-flash:free` | 模型，`provider:model` 形式 |
| `DEVELOPMENT_BASE_URL` | OpenRouter 网关 | 自定义 API 地址 |
| `OPENROUTER_API_KEY` / `OPENAI_API_KEY` / `DEEPSEEK_API_KEY` | 空 | 模型密钥（优先于 /login 保存的凭据） |
| `DEVMENTOR_LANGUAGE` | `zh` | 讲解语言，`zh` 或 `en` |
| `DEVMENTOR_PERMISSION_MODE` | `interactive` | 权限档位，见上文 |
| `DEVMENTOR_PROJECT_ROOT` | 当前目录 | 导师读写的代码目录 |
| `DEVMENTOR_WORKSPACE` | `.devmentor/workspace` | 工作区目录 |
| `DEVMENTOR_STATE_DIR` | `.devmentor/state` | 会话状态目录 |
| `DEVMENTOR_MAX_ITERS` | `24` | 单轮推理最大轮数 |
| `DEVMENTOR_JAVA_HOME` | 自动探测 | 指定 JDK 17+ |

```bash
# 例子：英文讲解 + 只读模式 + 数据放到别处
export DEVMENTOR_LANGUAGE=en
export DEVMENTOR_PERMISSION_MODE=read-only
export DEVMENTOR_WORKSPACE=~/devmentor-data/workspace
```

> 应用内也能改一部分：`/mode` 切权限、`/model` 换模型、`/login` 换凭据，这些立刻生效。

---

## 开发

```bash
# 后端快测（不依赖网络和 API Key）
cd backend && python -m pytest tests/ -q -m "not e2e"

# 后端全量测试（含 e2e，起真实子进程）
cd backend && python -m pytest tests/ -q

# 前端类型检查与构建
cd frontend && npx tsc --noEmit && npm run build

# 只跑后端（调试协议）
cd backend && python -m devmentor.server
# 然后手工喂 JSON：
#   {"type":"command","name":"session","args":[]}
#   {"type":"shutdown"}
```

### 会话文件与清理

会话状态存在 `.devmentor/state/<会话id>.json`，**默认保留最近 100 个**，更旧的自动删除。

为什么有上限：一个典型会话（20 轮对话）约 32KB。重度使用（每天 10 个会话）一年会累积约 110MB，
且此前没有任何清理机制。限制后占用稳定在约 3MB。

- 接续逻辑取最近的会话，清理不会把它删掉
- `/new` 开的旧会话会保留，方便回看
- 需要完整历史可以在代码里传 `SessionStore(dir, max_sessions=0)` 关闭限制

```bash
# 想看当前占用
du -sh .devmentor/state        # macOS / Linux
Get-ChildItem .devmentor/state | Measure-Object Length -Sum   # Windows
```

### 跨 Python 版本

声明支持 3.11+，但实际在 `datetime`、`asyncio` 等细节上版本间有差异。**改代码后建议至少用两个版本各跑一次**。

真实踩过的坑：Python 3.12 在同一进程内连续调用 `datetime.now()` 时微秒不前进，导致连开两个会话
拿到相同 id（3.13 上不复现），后一个会话会覆盖前一个。现在 id 里带了进程内自增序号。

### 调试协议

后端 stdout 只有协议 JSON，日志一律走 stderr。若你加了 `print()` 调试，
它会污染协议流——请用 `sys.stderr.write`（或 `server.log()`）。

---

## 设计取舍

- **前后端分开而不是单体**：渲染和推理的变更节奏完全不同。Ink 里改一个组件不该触发 Agent 重建；换模型不该动 UI 代码。
- **协议用 JSON-lines 而不是 HTTP**：单机 CLI 引入 HTTP 只增加启动开销和端口管理。stdio 天然随进程生命周期，无端口冲突。
- **前端保留一份命令表**：补全菜单要立即响应，不能等后端往返。命令执行仍由后端负责，前端表只影响补全体验——不同步也不会坏。
- **结论必须可验证**：导师唯一的能力锚点是"真跑一遍"。宁可说"这段我没执行过"，也不把猜的当成验证过的。
- **凭据环境变量优先**：CI 里注入的 Key 盖掉开发机个人 Key，避免流水线误用个人额度。