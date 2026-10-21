# DevMentor · Java 编程导师终端智能体

一个跑在终端里的 Java 学习伙伴。它不只回答问题，还会**真的编译并运行代码**来验证自己说的话，能按课程大纲带你学、给你出带验收标准的练习、跨会话记得你学到哪了。

装上之后，在终端敲四个字符就能开始：

```
$ devmentor
```

技术底座：[AgentScope Java 2.0.4](https://java.agentscope.io) 的 `HarnessAgent`（推理循环、工具、记忆、会话持久化）+ [JLine 3.30.17](https://github.com/jline/jline3)（行编辑、历史、补全、ANSI 渲染）+ 任意 OpenAI 兼容模型网关（默认 OpenRouter 免费模型）。

---

## 安装：让 `devmentor` 变成一条命令

装完后在任何目录敲 `devmentor` 就能启动，和 `claude`、`qoder` 的手感一样。

### 前置条件

**只需要 JDK 17+**（必须是 JDK，不是 JRE——导师要用内置编译器跑你的代码）。没有 Key 也能装能启动，登录在第一次对话时做。

### Windows（PowerShell）

```powershell
git clone https://github.com/dre4m1nd/devmentor.git
cd devmentor
powershell -ExecutionPolicy Bypass -File install.ps1
```

### macOS / Linux

```bash
git clone https://github.com/dre4m1nd/devmentor.git
cd devmentor
bash install.sh
```

### 安装脚本做了什么

1. 没有现成 JAR 时自动构建（需要 Maven；会依次找 `mvnw` 包装器、PATH 里的 `mvn`、常见安装目录）
2. 把 JAR 和启动脚本复制到安装目录：`~/.devmentor/lib/` 与 `~/.devmentor/bin/`
3. 把 `~/.devmentor/bin` 加进用户 PATH

```
~/.devmentor/
├── bin/
│   └── devmentor.cmd      # Windows
│   └── devmentor          # macOS / Linux
└── lib/
    └── devmentor.jar
```

> **装完要开一个新终端**（PATH 改了，已打开的窗口读不到）。
> 不想重开的话，当前窗口临时生效：
> ```powershell
> $env:PATH += ";$env:USERPROFILE\.devmentor\bin"   # Windows
> export PATH="$HOME/.devmentor/bin:$PATH"           # macOS / Linux
> ```

### 启动器怎么找 Java

按下面顺序挑第一个可用的 JDK 17+，所以你机器上装了多个 JDK 也不用配：

1. `DEVMENTOR_JAVA_HOME`（你显式指定的）
2. `~/.jdks/openjdk-17*`、`~/.jdks/openjdk-2*`（IDEA 下载的 JDK 常放这）
3. `JAVA_HOME`（指向的目录里得真有 `java`）
4. PATH 里的 `java`

都不满足时会打印一行明确提示，而不是抛栈：

```
[ERROR] Cannot find Java 17+. Install JDK 17 or set DEVMENTOR_JAVA_HOME.
```

### 指定安装位置 / 卸载

```powershell
# 装到别处
powershell -ExecutionPolicy Bypass -File install.ps1 -InstallDir "D:\tools\devmentor"
```

卸载就是删掉目录，再去 PATH 里去掉那一项：

```powershell
Remove-Item -Recurse -Force "$env:USERPROFILE\.devmentor"
# 然后在「系统属性 → 环境变量」里删掉 %USERPROFILE%\.devmentor\bin
```

### 不想装？直接跑 JAR

```bash
mvn -DskipTests package
java -jar target/devmentor-0.0.1-SNAPSHOT.jar
```

---

## 第一次对话：登录模型

启动后 banner 会告诉你现在有没有凭据：

```
  模型     openai:minimax/minimax-m3.1-flash:free
  凭据     未登录 — 输入 /login 选择厂商并填入 API Key
```

输入 `/login`，用上下键选厂商，回车确认，再粘贴 Key：

```
你 > /login
选择模型厂商：
  1) OpenRouter（免费模型，推荐）
  2) DeepSeek
  3) 阿里云百炼 DashScope
  4) OpenAI
  5) Anthropic Claude
  6) 本地 Ollama（无需 Key）

厂商序号 › 1
厂商：OpenRouter（免费模型，推荐）
获取 Key：https://openrouter.ai/keys
API Key › ****
✔ 凭据已保存到 C:\Users\you\.devmentor\credentials
✔ 已登录 OpenRouter，模型：openai:minimax/minimax-m3.1-flash:free
```

**不想注册任何服务**：选第 6 项 Ollama，本地模型不要 Key。

Key 的存储和优先级：

- 位置 `~/.devmentor/credentials`（不在项目里，不会误提交），POSIX 下权限 0600
- 输入时**掩码显示，且不写入命令历史**
- 优先级：**环境变量 > 本地凭据文件**。所以 CI 里注入 `OPENROUTER_API_KEY` 会盖掉你本机的个人 Key
- 换 Key：再执行一次 `/login`；清除：`/logout`

---

## 用法

直接输入问题即可：`解释一下泛型通配符`、`帮我看看这段代码有什么问题`、`给我出一道 Stream 的题`。

### 斜杠命令补全

输入 `/` 会立刻弹出候选菜单，用 **↑ ↓ 选择**、**Tab 或 Enter 确认**。命令有固定参数的（如 `/mode`）连参数也会补：

```
你 > /lo
  /login     登录：选择厂商并输入 API Key
  /logout    清除已保存的 API Key
```

### 斜杠命令一览

| 命令 | 作用 |
| --- | --- |
| `/help` | 显示帮助 |
| `/login` / `/logout [厂商]` | 登录厂商 / 清除凭据 |
| `/new [名字]` / `/reset` | 开新会话 / 清空当前上下文 |
| `/arch [路径]` | **架构评审**当前项目 |
| `/lesson [slug]` / `/progress` | 读课程 / 看学习进度 |
| `/mode <interactive\|read-only\|full>` | 切换权限档位 |
| `/plan [on\|off]` | 切换 plan 模式（只读设计阶段） |
| `/model [id]` / `/lang <zh\|en>` | 换模型 / 换讲解语言 |
| `/session` / `/workspace` / `/tools` | 查看会话 / 工作区 / 工具清单 |
| `/verbose` / `/think` | 切换工具输出全量 / 显示推理过程 |
| `/quit` | 退出 |

Ctrl+C 中断当前回答，Ctrl+D 退出。

### 架构评审（核心用法）

把它指向你正在开发的项目，它会独立读取并给出架构缺陷与改法：

```bash
# 对话中评审当前目录
/arch

# 指定路径
/arch D:\my-project

# 非交互：完整评审（需要模型）
devmentor --review D:\my-project

# 非交互：只看事实，不调模型。有发现退出码为 1（可做 CI 门槛）
devmentor --scan-only D:\my-project
```

评审分两段输出，请分清哪部分是证据、哪部分是建议：

1. **项目架构事实**（静态分析，可核对）：包结构、包级依赖图、体量最大的文件、规则命中清单
2. **架构评审**（模型的判断）：每条缺陷按「证据 / 影响 / 改法 / 顺序」四段写，最后给按「影响 ÷ 成本」排序的优先级表

确定性规则覆盖：上帝类、超长方法、**包级循环依赖**、分层倒置（repository 反向依赖 service）、包结构平铺、无测试、多包根、纯 POJO 误报过滤。

评审工具（模型也可在对话中直接调用）：`arch_scan` / `arch_findings` / `arch_dependencies` / `arch_file_profile` / `arch_read_source`。

### 命令行参数

| 参数 | 作用 |
| --- | --- |
| `--ask "..."` | 单轮提问后退出（适合脚本） |
| `--review [路径]` | **架构评审**：静态分析指定项目并给出缺陷与改法，然后退出 |
| `--scan-only [路径]` | 只打印静态分析事实，**不调用模型**；有发现时退出码 1（CI 可用） |
| `--self-check` | 打印配置、工作区、工具清单后退出，**不调用模型** |
| `--model <id>` | 覆盖模型，如 `ollama:qwen2.5-coder` |
| `--session <id>` | 指定会话 id |
| `--mode <profile>` | `interactive`（默认）/ `read-only` / `full` |
| `--no-color` | 关闭颜色 |
| `--verbose` | 工具输出全量而非摘要 |
| `--think` | 显示推理过程 |

---

## 权限档位

导师能读写你的代码目录，所以权限是分档的：

| 档位 | 行为 |
| --- | --- |
| `interactive`（默认） | 读文件、列目录、跑代码**自动放行**；`write_file` / `edit_file` / `execute` / `skill_manage` **每次询问 y/N** |
| `read-only` | 只读，任何写操作直接被拒绝（适合"只讲讲，别动我代码"） |
| `full` | 全部放行，不再询问（谨慎使用） |

被拒绝时，拒绝原因会回写给模型，它会换个方案而不是卡死。

---

## 配置

全部可配项在 `application.yaml` 的 `devmentor.*` 下，也可用环境变量覆盖：

```yaml
devmentor:
  model-id: ${DEVELOPMENT_MODEL_ID:openai:minimax/minimax-m3.1-flash:free}
  api-key: ${OPENROUTER_API_KEY:}          # 只从环境变量读取
  base-url: ${DEVELOPMENT_BASE_URL:https://openrouter.ai/api/v1}
  workspace: .devmentor/workspace          # 人设、课程、技能、记忆
  state-dir: .devmentor/state              # 会话状态
  project-root: ""                         # 空 = 当前目录（导师读写的代码位置）
  permission-mode: interactive
  max-iters: 24
  enable-shell: false                      # 默认不开放宿主机 shell
  tools.java-run.timeout-seconds: 10
```

### 日志

启动时**不打印框架日志**，终端上只有 banner 和对话。需要排查问题时放开：

```powershell
$env:DEVMENTOR_LOG_LEVEL = "debug"    # Windows
export DEVMENTOR_LOG_LEVEL=debug      # macOS / Linux
```

### 换模型

任何 `provider:model` 形式的 id 都可以，只要 classpath 里有对应 provider 扩展：

```bash
--model openai:minimax/minimax-m3.1-flash:free   # OpenRouter 免费（已内置）
--model deepseek:deepseek-chat                    # DeepSeek
--model ollama:qwen2.5-coder                      # 本地 Ollama
```

> 免费模型有配额和限流（`429`/`403` 很常见）。遇到时用 `/model` 换一个，或稍后重试。

---

## 导师能做什么

| 工具 | 作用 |
| --- | --- |
| `java_compile_check` | 用 JDK 编译器检查片段，返回 `行:列` 诊断 |
| `java_run_snippet` | **真正编译并运行**，返回退出码、stdout、stderr，超时强杀 |
| `curriculum_list` / `curriculum_read` | 读取工作区里的 8 篇课程 |
| `progress_read` / `progress_record` | 记录/回顾学习进度（跨会话） |

此外还有 Harness 自带的能力：读写文件、grep/glob、长期记忆、会话搜索、plan 模式、技能管理。

## 工作区结构

```text
.devmentor/workspace/
├── AGENTS.md              # 导师人设（可自由修改，下轮生效）
├── preferences.md         # 你的偏好：语言、深度、是否先给提示
├── progress.md            # 学习进度（由导师记录）
├── curriculum/            # 8 篇课程：语法 → OOP → 集合 → Stream → 异常 → 并发 → JVM → 测试
└── skills/                # 代码评审 / 调试教练 / 出题助手 / 架构评审
```

这些人设和课程都是普通 Markdown，**直接编辑即可**，不需要改代码、不需要重新编译。

---

## 开发

```bash
mvn test                    # 111 个离线单测，不依赖网络和 API Key
mvn -DskipTests package
```

测试覆盖：架构规则与语法树扫描、项目快照、配置绑定、缺 Key 的友好报错、工作区幂等落盘、
Java 片段的编译/运行/超时/超长拒绝、路径穿越防护、命令解析、命令补全（含真实 JLine parser 链路）、
凭据存储、厂商目录、终端渲染、权限档位映射。

> 构建时注意：本机 `JAVA_HOME` 若指向 JDK 11 或更低，需显式切到 JDK 17。

## 设计取舍

- **用 JLine 而不是 Spring Shell**：Spring Shell 的命令解析器会把自由聊天文本当命令、回一句 "Command not found"，和导师对话场景冲突。
- **全局命令用「安装目录 + PATH」而不是 `npm i -g` 那类包管理器**：项目是单 JAR，没有依赖图需要管理；把 JAR 和启动脚本放一处、把 bin 目录挂到 PATH，是最少活动部件的做法。
- **启动器按目录名扫 JDK 而不是解析 `java -version`**：版本探测要起子进程、读 stderr，在不同 shell 下还容易把警告当错误；按 `openjdk-17*` 这类目录名匹配更稳，也更快。
- **凭据优先级是环境变量 > 本地文件**：CI 里注入的 Key 会盖掉开发机 `/login` 存的个人 Key，避免流水线误用个人额度。
- **斜杠命令补全自己接管 `self-insert`**：JLine 的 `AUTO_LIST` 只在按 Tab 触发的 `doComplete` 里生效，打字时根本不会调用 completer。要在输入 `/` 的瞬间弹菜单，只能包一层 `self-insert`。同时它只在真实终端启用——管道输入下 JLine 逐字符喂入，弹菜单会把后续字符当导航键吃掉（`/quit` 会变成 `/archquit`）。
- **interactive 档位用 `ACCEPT_EDITS` 而非 `DEFAULT`**：`DEFAULT` 的兜底是"一切都要确认"，连 `read_file` 都弹窗，实际不可用。
- **模型 bean 延迟创建**：没有 Key 时上下文仍能启动，`--self-check` 因此可以在离线环境下做装配检查。
- **`java_run_snippet` 按类型名命名源文件**：`public class Foo` 必须存在 `Foo.java` 里，否则 javac 直接拒绝。