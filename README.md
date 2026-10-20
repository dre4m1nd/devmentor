# DevMentor · Java 编程导师终端智能体

一个跑在终端里的 Java 学习伙伴。它不只回答问题，还会**真的编译并运行代码**来验证自己说的话，能按课程大纲带你学、给你出带验收标准的练习、跨会话记得你学到哪了。

技术底座：[AgentScope Java 2.0.4](https://java.agentscope.io) 的 `HarnessAgent`（推理循环、工具、记忆、会话持久化）+ [JLine 3.30.17](https://github.com/jline/jline3)（行编辑、历史、补全、ANSI 渲染）+ 任意 OpenAI 兼容模型网关（默认 OpenRouter 免费模型）。

## 快速开始

需要 **JDK 17+**（必须是 JDK，不是 JRE —— 导师要用内置编译器跑你的代码）。

```bash
# 1. 设置模型密钥（只从环境变量读取，不会写进仓库）
set OPENROUTER_API_KEY=sk-or-...        # Windows
export OPENROUTER_API_KEY=sk-or-...     # macOS / Linux

# 2. 构建
mvn -DskipTests package

# 3. 开始对话
java -jar target/devmentor-0.0.1-SNAPSHOT.jar
```

首次启动会在 `.devmentor/workspace` 落盘导师人设、8 篇课程和 4 个技能，之后不会覆盖你的修改。

## 用法

直接输入问题即可，例如「解释一下泛型通配符」「帮我看看这段代码有什么问题」「给我出一道 Stream 的题」。

### 架构评审（核心用法）

把它指向你正在开发的项目，它会独立读取并给出架构缺陷与改法：

```bash
# 完整评审（需要模型）：先做确定性静态分析，再让模型基于事实判断
java -jar target/devmentor-0.0.1-SNAPSHOT.jar --review D:\my-project

# 只看事实，不调模型：任何发现都让退出码为 1（CI 门槛可用）
java -jar target/devmentor-0.0.1-SNAPSHOT.jar --scan-only D:\my-project
```

评审分两段输出，请分清哪部分是证据、哪部分是建议：

1. **项目架构事实**（静态分析，可核对）：包结构、包级依赖图、体量最大的文件、规则命中清单
2. **架构评审**（模型的判断）：每条缺陷按「证据 / 影响 / 改法 / 顺序」四段写，最后给按「影响 ÷ 成本」排序的优先级表

确定性规则覆盖：上帝类、超长方法、**包级循环依赖**、分层倒置（repository 反向依赖 service）、包结构平铺、无测试、多包根、纯 POJO 误报过滤。

评审工具（模型也可在对话中直接调用）：`arch_scan` / `arch_findings` / `arch_dependencies` / `arch_file_profile` / `arch_read_source`。交互模式里输入 `/arch [路径]` 同样会做评审。

### 命令行参数

| 参数 | 作用 |
| --- | --- |
| `--ask "..."` | 单轮提问后退出（适合脚本） |
| `--review [路径]` | **架构评审**：静态分析指定项目并给出缺陷与改法，然后退出 |
| `--scan-only [路径]` | 只打印静态分析事实，**不调用模型**；有发现时退出码 1（CI 可用） |
| `--self-check` | 打印配置、工作区、工具清单后退出，**不调用模型** |
| `--model <id>` | 覆盖模型，如 `openai:cohere/north-mini-code:free` |
| `--session <id>` | 指定会话 id |
| `--mode <profile>` | `interactive`（默认）/ `read-only` / `full` |
| `--no-color` | 关闭颜色 |
| `--verbose` | 工具输出全量而非摘要 |
| `--think` | 显示推理过程 |

### 斜杠命令

`/help` `/new` `/reset` `/mode` `/plan` `/lesson` `/progress` `/lang` `/model` `/tools` `/workspace` `/session` `/verbose` `/think` `/quit`

## 权限档位

导师能读写你的代码目录，所以权限是分档的：

| 档位 | 行为 |
| --- | --- |
| `interactive`（默认） | 读文件、列目录、跑代码**自动放行**；`write_file` / `edit_file` / `execute` / `skill_manage` **每次询问 y/N** |
| `read-only` | 只读，任何写操作直接被拒绝（适合"只讲讲，别动我代码"） |
| `full` | 全部放行，不再询问（谨慎使用） |

被拒绝时，拒绝原因会回写给模型，它会换个方案而不是卡死。

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

### 换模型

任何 `provider:model` 形式的 id 都可以，只要 classpath 里有对应 provider 扩展：

```bash
--model openai:cohere/north-mini-code:free        # OpenRouter（已内置）
--model dashscope:qwen-plus                        # 需加 agentscope-extensions-model-dashscope
--model ollama:qwen2.5-coder                       # 需加 agentscope-extensions-model-ollama
```

> 免费模型有配额和限流（`429`/`403` 很常见）。遇到时用 `/model` 换一个，或稍后重试。

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
└── skills/                # 代码评审 / 调试教练 / 出题助手
```

这些人设和课程都是普通 Markdown，**直接编辑即可**，不需要改代码、不需要重新编译。

## 开发

```bash
mvn test          # 53 个离线单测，不依赖网络和 API Key
mvn -DskipTests package
```

测试覆盖：配置绑定、缺 Key 的友好报错、工作区幂等落盘（含 SKILL.md frontmatter 可解析）、
Java 片段的编译/运行/超时/超长拒绝、路径穿越防护、命令解析、终端渲染、权限档位映射。

> 构建时注意：本机 `JAVA_HOME` 若指向 JDK 11，需显式切到 JDK 17。

## 设计取舍

- **用 JLine 而不是 Spring Shell**：Spring Shell 的命令解析器会把自由聊天文本当命令、回一句 "Command not found"，和导师对话场景冲突。
- **interactive 档位用 `ACCEPT_EDITS` 而非 `DEFAULT`**：`DEFAULT` 的兜底是"一切都要确认"，连 `read_file` 都弹窗，实际不可用。
- **模型 bean 延迟创建**：没有 Key 时上下文仍能启动，`--self-check` 因此可以在离线环境下做装配检查。
- **`java_run_snippet` 按类型名命名源文件**：`public class Foo` 必须存在 `Foo.java` 里，否则 javac 直接拒绝。
