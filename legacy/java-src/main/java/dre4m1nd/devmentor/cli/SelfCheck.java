package dre4m1nd.devmentor.cli;

import dre4m1nd.devmentor.agent.MentorAgentFactory;
import dre4m1nd.devmentor.agent.PermissionProfiles;
import dre4m1nd.devmentor.config.DevMentorConfigException;
import dre4m1nd.devmentor.config.MentorProperties;
import io.agentscope.core.model.Model;
import io.agentscope.core.model.ModelCreationContext;
import io.agentscope.core.model.ModelRegistry;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.stream.Stream;

/**
 * 自检：不调用模型，只打印解析后的配置、工作区状态与工具清单。
 *
 * <p>用于在没有网络或没有 Key 的环境里确认「装配是否正确」，也是 CI 的冒烟入口。
 */
public final class SelfCheck {

    private SelfCheck() {}

    /**
     * @return 进程退出码：0 正常，1 有阻断性问题
     */
    public static int run(MentorProperties props, MentorAgentFactory factory, CliOptions options) {
        // 先落盘模板，让自检反映「真正可用」的状态，而不是首次运行前的空目录。
        try {
            factory.prepareWorkspace();
        } catch (RuntimeException ignored) {
            // 准备失败会在下面的检查项里体现
        }
        StringBuilder sb = new StringBuilder();
        sb.append("DevMentor 自检").append(System.lineSeparator());
        sb.append("──────────────").append(System.lineSeparator());
        sb.append("模型 id      : ").append(props.getModelId()).append(System.lineSeparator());
        sb.append("base url     : ")
                .append(isBlank(props.getBaseUrl()) ? "(provider 默认)" : props.getBaseUrl())
                .append(System.lineSeparator());
        sb.append("API Key      : ")
                .append(isBlank(props.getApiKey()) ? "未配置" : "已配置")
                .append(System.lineSeparator());
        sb.append("语言         : ").append(props.getLanguage()).append(System.lineSeparator());
        sb.append("用户 / 会话  : ")
                .append(props.getUserId())
                .append(" / ")
                .append(isBlank(props.getSessionId()) ? "(自动生成)" : props.getSessionId())
                .append(System.lineSeparator());
        sb.append("权限档位     : ")
                .append(PermissionProfiles.describe(props.getPermissionMode()))
                .append(System.lineSeparator());
        sb.append("工作区       : ").append(factory.workspaceDir()).append(System.lineSeparator());
        sb.append("状态目录     : ").append(factory.stateDir()).append(System.lineSeparator());
        sb.append("代码目录     : ").append(factory.projectRoot()).append(System.lineSeparator());
        sb.append("shell 工具   : ").append(props.isEnableShell() ? "开启" : "关闭").append(System.lineSeparator());

        int problems = 0;

        // 1. 模型是否可解析（不发起请求）
        boolean modelResolvable = false;
        try {
            Model model = resolveQuietly(props);
            modelResolvable = model != null;
            sb.append("模型解析     : ")
                    .append(modelResolvable ? "OK (" + model.getModelName() + ")" : "未解析")
                    .append(System.lineSeparator());
        } catch (RuntimeException e) {
            sb.append("模型解析     : 失败 - ").append(e.getMessage()).append(System.lineSeparator());
        }
        if (!modelResolvable && isBlank(props.getApiKey()) && !props.getModelId().startsWith("ollama:")) {
            problems++;
            sb.append("  ↳ 缺少 API Key：设置 OPENROUTER_API_KEY 后才能真实对话。")
                    .append(System.lineSeparator());
        }

        // 2. 工作区是否就绪
        Path workspace = factory.workspaceDir();
        sb.append("AGENTS.md    : ")
                .append(Files.isRegularFile(workspace.resolve("AGENTS.md")) ? "存在" : "缺失")
                .append(System.lineSeparator());
        long lessons = countLessons(workspace.resolve("curriculum"));
        sb.append("课程数量     : ").append(lessons).append(System.lineSeparator());
        long skills = countSkills(workspace.resolve("skills"));
        sb.append("技能数量     : ").append(skills).append(System.lineSeparator());
        if (!Files.isRegularFile(workspace.resolve("AGENTS.md")) || lessons == 0) {
            problems++;
            sb.append("  ↳ 工作区未初始化：启动一次交互模式即可自动落盘模板。")
                    .append(System.lineSeparator());
        }

        // 3. 工具清单（只装配 Toolkit，不创建 Agent，因此不需要模型可用）
        try {
            List<String> tools =
                    factory.buildToolkit(factory.workspaceDir()).getToolNames().stream()
                            .sorted()
                            .toList();
            sb.append("工具数量     : ").append(tools.size()).append(System.lineSeparator());
            sb.append("工具清单     : ").append(String.join(", ", tools)).append(System.lineSeparator());
            for (String required : List.of("java_compile_check", "java_run_snippet", "curriculum_read", "progress_read")) {
                if (!tools.contains(required)) {
                    problems++;
                    sb.append("  ↳ 缺少工具：").append(required).append(System.lineSeparator());
                }
            }
        } catch (RuntimeException e) {
            problems++;
            sb.append("工具装配失败 : ").append(rootMessage(e)).append(System.lineSeparator());
        }

        sb.append("──────────────").append(System.lineSeparator());
        sb.append(problems == 0 ? "结论         : 可以正常使用 ✅" : "结论         : 有 " + problems + " 项需要处理 ⚠")
                .append(System.lineSeparator());

        System.out.println(sb);
        if (options != null && options.isVerbose()) {
            System.out.println("（verbose 模式不额外输出）");
        }
        return problems == 0 ? 0 : 1;
    }

    private static Model resolveQuietly(MentorProperties props) {
        String apiKey = isBlank(props.getApiKey()) ? null : props.getApiKey().trim();
        if (apiKey == null && !props.getModelId().startsWith("ollama:")) {
            return null;
        }
        ModelCreationContext.Builder ctx = ModelCreationContext.builder().stream(Boolean.TRUE);
        if (apiKey != null) {
            ctx.apiKey(apiKey);
        }
        if (!isBlank(props.getBaseUrl())) {
            ctx.baseUrl(props.getBaseUrl().trim());
        }
        return ModelRegistry.resolve(props.getModelId(), ctx.build());
    }

    private static long countLessons(Path dir) {
        if (!Files.isDirectory(dir)) {
            return 0;
        }
        try (Stream<Path> stream = Files.list(dir)) {
            return stream.filter(Files::isRegularFile).filter(p -> p.toString().endsWith(".md")).count();
        } catch (Exception e) {
            return 0;
        }
    }

    private static long countSkills(Path dir) {
        if (!Files.isDirectory(dir)) {
            return 0;
        }
        try (Stream<Path> stream = Files.walk(dir)) {
            return stream.filter(Files::isRegularFile)
                    .filter(p -> "SKILL.md".equals(p.getFileName().toString()))
                    .count();
        } catch (Exception e) {
            return 0;
        }
    }

    private static boolean isBlank(String value) {
        return value == null || value.isBlank();
    }

    private static String rootMessage(Throwable t) {
        Throwable cur = t;
        while (cur.getCause() != null && cur.getCause() != cur) {
            cur = cur.getCause();
        }
        return cur.getMessage() == null ? cur.getClass().getSimpleName() : cur.getMessage();
    }
}
