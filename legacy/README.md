# Legacy：重构前的 Java 版

这个目录保存 DevMentor **重构前**的实现，仅供查阅与对照，**不再维护，也不要用来运行本项目**。

## 为什么放在这里

项目最初是单体的 Java 版（Spring Boot + AgentScope Java + JLine），
后来重构为 **Python 后端 + Node/Ink 前端** 的两层架构。

重构后 Java 版的所有功能都已在 Python 侧重新实现，包括：

- 架构分析引擎（改用 tree-sitter 解析，思路一致）
- 11 个 Agent 工具
- 权限三档、会话持久化

因此 Java 版处于废弃状态。保留它是因为：

1. git 历史里能查到，但直接放在根目录会让人误以为项目有两个版本
2. 部分注释和设计取舍在迁移时被沿用，留作参照

## 目录内容

| 路径 | 说明 |
| --- | --- |
| `java-src/` | 重构前的 Java 源码（Spring Boot 应用） |
| `pom.xml` | Maven 配置 |
| `mvn-wrapper/` | 原 `.mvn/`，Maven Wrapper 配置 |
| `install.ps1` / `install.sh` | 旧版安装脚本（装 Java JAR 并挂 PATH） |
| `bin/` | 旧版启动脚本（`devmentor.cmd` / `devmentor`，指向 JAR） |

## 当前版本怎么用

看根目录的 [README](../README.md)。简要说：

```bash
cd backend && pip install -e .        # Python 后端依赖
cd frontend && npm install && npm run build   # Ink 前端
node frontend/dist/cli.js             # 启动
```

## 对照参考

重构时保留的取舍在新代码里都有对应注释，例如：

- `backend/devmentor/arch/scanner.py` 顶部说明了"用 tree-sitter 而非完整编译"的理由
- `backend/devmentor/agent.py` 里 `_permission_for` 说明了权限三档的映射

想了解某个设计的来龙去脉，可以先看新代码的注释，再回这里找原始实现。
