# DevMentor · 编程导师终端智能体

终端里的编程学习伙伴。它不只回答问题，还会**真的编译并运行代码**验证自己说的话，能按课程大纲带你学、出带验收标准的练习、跨会话记得你学到哪。

在终端敲一行就能开始：

```
$ devmentor
```

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
│  · 11 个工具                 │
│  · 架构分析引擎              │
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

```bash
git clone https://github.com/dre4m1nd/devmentor.git
cd devmentor

# 后端依赖
cd backend && pip install agentscope pydantic && cd ..

# 前端依赖与构建
cd frontend && npm install && npm run build && cd ..

# 启动
node frontend/dist/cli.js
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
| `/help` | 显示帮助 |
| `/login` / `/logout [厂商]` | 登录厂商 / 清除凭据 |
| `/new [名字]` / `/reset` | 开新会话 / 清空当前上下文 |
| `/arch [路径]` | **架构评审**当前项目 |
| `/lesson [slug]` / `/progress` | 读课程 / 看学习进度 |
| `/mode <interactive read-only full>` | 切换权限档位 |
| `/plan [on off]` | 切换 plan 模式 |
| `/model [id]` / `/lang <zh en>` | 换模型 / 换讲解语言 |
| `/session` / `/workspace` / `/tools` | 查看会话 / 工作区 / 工具 |
| `/verbose` / `/think` | 工具输出全量 / 显示推理 |
| `/quit` | 退出 |

### 架构评审（核心用法）

```bash
# 对话中评审当前目录
/arch

# 指定路径
/arch D:\my-project
```

评审分两段，请分清哪部分是证据、哪部分是建议：

1. **项目架构事实**（静态分析，可核对）：包结构、包级依赖图、体量最大的文件、规则命中清单
2. **架构评审**（模型的判断）：每条缺陷按「证据 / 影响 / 改法 / 顺序」四段写，最后给按「影响 ÷ 成本」排序的优先级表

确定性规则（9 条）：上帝类、超长方法、方法过多（过滤纯 POJO）、包结构平铺、**包级循环依赖**、分层倒置、无测试、无注释、多包根。

> **当前能力边界**：架构分析引擎解析 **Java** 源码；代码真跑验证（`java_run_snippet`）也是 Java。
> 讲解其它语言没有问题，但这两项能力暂不支持——导师会明确说明，不会假装验证过。

约束模型的铁律：**在没调用 `arch_scan` 之前，不给出任何架构意见。**

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
│   │   ├── arch/                 架构分析引擎
│   │   │   ├── scanner.py        tree-sitter 扫描
│   │   │   ├── model.py          项目快照（纯事实）
│   │   │   ├── rules.py          9 条规则（纯判断）
│   │   │   └── analyzer.py       入口与报告
│   │   └── tools/                11 个 Agent 工具
│   └── tests/                    77 个测试
└── frontend/                     Ink 终端 UI
    └── src/
        ├── types.ts              协议类型
        ├── backend.ts            子进程管理与 JSON 行读写
        ├── commands.ts           命令表与补全数据
        └── components/           Banner / EntryView / ConfirmBox / Prompt / App
```

---

## 开发

```bash
# 后端测试（不依赖网络和 API Key）
cd backend && python -m pytest tests/ -q

# 前端类型检查与构建
cd frontend && npx tsc --noEmit && npm run build

# 只跑后端（调试协议）
cd backend && python -m devmentor.server
# 然后手工喂 JSON：
#   {"type":"command","name":"help","args":[]}
#   {"type":"shutdown"}
```

### 调试协议

后端 stdout 只有协议 JSON，日志一律走 stderr。若你加了 `print()` 调试，
它会污染协议流——请用 `sys.stderr.write`（或 `server.log()`）。

---

## 设计取舍

- **前后端分开而不是单体**：渲染和推理的变更节奏完全不同。Ink 里改一个组件不该触发 Agent 重建；换模型不该动 UI 代码。
- **协议用 JSON-lines 而不是 HTTP**：单机 CLI 引入 HTTP 只增加启动开销和端口管理。stdio 天然随进程生命周期，无端口冲突。
- **前端保留一份命令表**：补全菜单要立即响应，不能等后端往返。命令执行仍由后端负责，前端表只影响补全体验——不同步也不会坏。
- **架构分析用 tree-sitter 而不是完整编译**：与之前 Java 版同一个取舍——评审任意用户项目时，不能要求它依赖齐全、构建可跑。tree-sitter 只需要 `.java` 文件本身。
- **事实与判断分离**：`ProjectSnapshot` 只有结构事实，`rules.py` 只有确定性判断，模型只拿到带证据的清单。这是防止 AI Code Review 说空话的根本手段。
- **凭据环境变量优先**：CI 里注入的 Key 盖掉开发机个人 Key，避免流水线误用个人额度。