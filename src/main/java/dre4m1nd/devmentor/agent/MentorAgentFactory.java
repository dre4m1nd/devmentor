package dre4m1nd.devmentor.agent;

import dre4m1nd.devmentor.config.MentorProperties;
import dre4m1nd.devmentor.tools.ArchitectureTools;
import dre4m1nd.devmentor.tools.CurriculumTools;
import dre4m1nd.devmentor.tools.JavaSnippetTools;
import dre4m1nd.devmentor.tools.ProgressTools;
import dre4m1nd.devmentor.workspace.WorkspaceBootstrapper;
import io.agentscope.core.model.Model;
import io.agentscope.core.state.JsonFileAgentStateStore;
import io.agentscope.core.tool.Toolkit;
import io.agentscope.harness.agent.HarnessAgent;
import io.agentscope.harness.agent.filesystem.spec.LocalFilesystemSpec;
import io.agentscope.harness.agent.memory.compaction.CompactionConfig;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.function.Supplier;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * 把工作区、模型、工具、权限、记忆组装成一个可用的导师 Agent。
 */
public class MentorAgentFactory {

    private static final Logger log = LoggerFactory.getLogger(MentorAgentFactory.class);

    /** AGENTS.md 读不到时的兜底人设，保证任何情况下都能用。 */
    static final String FALLBACK_SYSTEM_PROMPT =
            """
            你是 DevMentor，一位耐心、严格的 Java 编程导师。

            - 先诊断再给答案：问清目标、已尝试的方案和报错，再决定怎么讲。
            - 结论必须可验证：凡是声称"能运行"的代码，先用 java_run_snippet 真正跑一遍。
            - 一次只讲一个概念，用 Java 17 语法，给最小可运行示例。
            - 练习要附验收标准；学习者卡住时先给提示，不要直接贴答案。
            - 默认用中文讲解，代码与术语保留英文。
            """;

    private final MentorProperties props;
    private final Supplier<Model> modelSupplier;
    private final WorkspaceBootstrapper bootstrapper;

    public MentorAgentFactory(
            MentorProperties props, Model model, WorkspaceBootstrapper bootstrapper) {
        this(props, () -> model, bootstrapper);
    }

    /**
     * 用 {@link Supplier} 延迟获取模型：这样即使还没有 API Key，工厂与工作区也能先准备好，
     * {@code --self-check} 因此可以在离线环境下工作。
     */
    public MentorAgentFactory(
            MentorProperties props, Supplier<Model> modelSupplier, WorkspaceBootstrapper bootstrapper) {
        this.props = props;
        this.modelSupplier = modelSupplier;
        this.bootstrapper = bootstrapper;
    }

    /** 解析工作区目录（相对路径按当前工作目录解析）。 */
    public Path workspaceDir() {
        return Path.of(props.getWorkspace()).toAbsolutePath().normalize();
    }

    /** 解析状态目录。 */
    public Path stateDir() {
        return Path.of(props.getStateDir()).toAbsolutePath().normalize();
    }

    /** 解析用户代码目录；未配置时用当前工作目录。 */
    public Path projectRoot() {
        String configured = props.getProjectRoot();
        if (configured == null || configured.isBlank()) {
            return Path.of(System.getProperty("user.dir")).toAbsolutePath().normalize();
        }
        return Path.of(configured).toAbsolutePath().normalize();
    }

    /**
     * 准备工作区：创建目录并落盘缺失的模板文件。
     *
     * @return 本次实际写入的相对路径
     */
    public java.util.List<String> prepareWorkspace() {
        Path workspace = workspaceDir();
        try {
            Files.createDirectories(workspace);
        } catch (IOException e) {
            throw new UncheckedIOException("无法创建工区目录: " + workspace, e);
        }
        return bootstrapper.ensure();
    }

    /**
     * 组装 Agent。
     *
     * @return 已就绪的 {@link HarnessAgent}，调用方负责 close
     */
    public HarnessAgent create() {
        Path workspace = workspaceDir();
        prepareWorkspace();

        String sysPrompt = WorkspaceBootstrapper.readIfPresent(workspace.resolve("AGENTS.md"));
        if (sysPrompt.isBlank()) {
            sysPrompt = FALLBACK_SYSTEM_PROMPT;
        }

        Toolkit toolkit = buildToolkit(workspace);

        HarnessAgent.Builder builder =
                HarnessAgent.builder()
                        .name("devmentor")
                        .agentId("devmentor")
                        .sysPrompt(sysPrompt)
                        .model(modelSupplier.get())
                        .workspace(workspace)
                        .filesystem(
                                new LocalFilesystemSpec()
                                        .project(projectRoot())
                                        .projectWritable(true))
                        .stateStore(new JsonFileAgentStateStore(stateDir()))
                        .toolkit(toolkit)
                        .maxIters(props.getMaxIters())
                        .permissionContext(PermissionProfiles.of(props.getPermissionMode()))
                        .compaction(
                                CompactionConfig.builder()
                                        .triggerMessages(props.getMaxHistoryMessages())
                                        .build())
                        // 会话转录固定在工作区内，避免 Harness 在项目根目录建 learner/ 之类的目录。
                        .transcriptStore(
                                new io.agentscope.harness.agent.transcript.FilesystemTranscriptStore(
                                        workspace.resolve(".transcripts")))
                        .additionalContextFile("preferences.md")
                        .enablePlanMode(props.isEnablePlanMode())
                        .enableSkillManageTool(props.isEnableSkillManage());

        if (!props.isEnableShell()) {
            // 默认不把宿主机 shell 暴露给模型；需要时显式打开 devmentor.enable-shell。
            builder.disableShellTool();
        }

        HarnessAgent agent = builder.build();
        log.info(
                "导师已就绪: model={} workspace={} project={} permission={} tools={}",
                props.getModelId(),
                workspace,
                projectRoot(),
                PermissionProfiles.describe(props.getPermissionMode()),
                agent.getToolkit().getToolNames().size());
        return agent;
    }

    /** 注册教学类工具（全部无状态，可被 Toolkit 的浅拷贝共享）。 */
    public Toolkit buildToolkit(Path workspace) {
        Toolkit toolkit = new Toolkit();
        MentorProperties.JavaRun javaRun = props.getTools().getJavaRun();
        if (javaRun.isEnabled()) {
            toolkit.registerTool(
                    new JavaSnippetTools(javaRun.getTimeoutSeconds(), javaRun.getMaxSourceChars()));
        }
        toolkit.registerTool(new CurriculumTools(workspace));
        toolkit.registerTool(new ProgressTools(workspace));
        if (props.getTools().getArch().isEnabled()) {
            toolkit.registerTool(new ArchitectureTools(projectRoot(), workspace.resolve("reports")));
        }
        return toolkit;
    }
}
