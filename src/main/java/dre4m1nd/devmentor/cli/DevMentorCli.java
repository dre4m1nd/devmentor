package dre4m1nd.devmentor.cli;

import dre4m1nd.devmentor.agent.MentorAgentFactory;
import dre4m1nd.devmentor.arch.ArchFinding;
import dre4m1nd.devmentor.arch.ArchitectureAnalyzer;
import dre4m1nd.devmentor.agent.MentorSession;
import dre4m1nd.devmentor.agent.PermissionProfiles;
import dre4m1nd.devmentor.config.DevMentorConfigException;
import dre4m1nd.devmentor.config.CredentialStore;
import dre4m1nd.devmentor.config.MentorProperties;
import dre4m1nd.devmentor.config.ProviderCatalog;
import io.agentscope.core.agent.RuntimeContext;
import io.agentscope.core.event.AgentEvent;
import io.agentscope.core.event.AgentEventType;
import io.agentscope.core.event.RequireUserConfirmEvent;
import io.agentscope.core.event.ToolCallStartEvent;
import io.agentscope.core.message.Msg;
import io.agentscope.core.message.UserMessage;
import io.agentscope.core.permission.PermissionMode;
import io.agentscope.core.event.ConfirmResult;
import io.agentscope.core.message.ToolUseBlock;
import io.agentscope.harness.agent.HarnessAgent;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.concurrent.atomic.AtomicReference;
import org.jline.keymap.KeyMap;
import org.jline.reader.Binding;
import org.jline.reader.Candidate;
import org.jline.reader.Reference;
import org.jline.reader.Widget;
import org.jline.utils.InfoCmp;
import org.jline.reader.EndOfFileException;
import org.jline.reader.LineReader;
import org.jline.reader.LineReaderBuilder;
import org.jline.reader.ParsedLine;
import org.jline.reader.UserInterruptException;
import org.jline.reader.impl.DefaultParser;
import org.jline.reader.impl.history.DefaultHistory;
import org.jline.terminal.Terminal;
import org.jline.terminal.TerminalBuilder;
import org.jline.utils.AttributedStyle;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

/**
 * 终端交互主循环：JLine 负责行编辑、历史、补全与 ANSI 渲染，Agent 负责推理与工具。
 */
@Component
@ConditionalOnProperty(prefix = "devmentor.cli", name = "enabled", matchIfMissing = true)
public class DevMentorCli implements ApplicationRunner {

    private static final Logger log = LoggerFactory.getLogger(DevMentorCli.class);

    private final MentorProperties props;
    private final MentorAgentFactory factory;
    private final CredentialStore credentialStore;

    private HarnessAgent agent;
    private MentorSession session;
    private Terminal terminal;
    private LineReader reader;
    private TerminalRenderer renderer;

    private boolean showThinking;
    private boolean verbose;
    private boolean color;

    public DevMentorCli(
            MentorProperties props, MentorAgentFactory factory, CredentialStore credentialStore) {
        this.props = props;
        this.factory = factory;
        this.credentialStore = credentialStore;
    }

    @Override
    public void run(ApplicationArguments applicationArguments) throws Exception {
        CliOptions options = CliOptions.parse(applicationArguments.getSourceArgs());

        if (options.getModel() != null) {
            props.setModelId(options.getModel());
        }
        if (options.getMode() != null) {
            props.setPermissionMode(options.getMode());
        }
        if (options.getSession() != null) {
            props.setSessionId(options.getSession());
        }
        this.showThinking = options.isThink();
        this.verbose = options.isVerbose();

        if (options.isSelfCheck()) {
            int code = SelfCheck.run(props, factory, options);
            if (code != 0) {
                System.exit(code);
            }
            return;
        }

        // --scan-only 不需要模型，因此放在 Agent 创建之前，无 Key 也能用。
        if (options.isScanOnly()) {
            runScanOnly(options.getReviewPath());
            return;
        }

        // Agent 延迟初始化：首次 ask() 时才创建，缺 Key 时先启动 REPL 再提示

        this.session = new MentorSession(props.getUserId(), props.getSessionId());
        // agent 延迟创建，首次 ask 时初始化
        this.terminal =
                TerminalBuilder.builder()
                        .name("devmentor")
                        .system(true)
                        .encoding(StandardCharsets.UTF_8)
                        .build();
        this.color = !options.isNoColor() && supportsColor();
        PrintWriter out = terminal.writer();
        this.renderer = new TerminalRenderer(out, color, showThinking, verbose);
        this.reader = buildLineReader();

        Runtime.getRuntime()
                .addShutdownHook(
                        new Thread(
                                () -> {
                                    try {
                                        if (agent != null) {
                                            agent.interrupt();
                                            agent.close();
                                        }
                                    } catch (Exception ignored) {
                                        // 关停阶段不再抛错
                                    }
                                },
                                "devmentor-shutdown"));

        if (options.isReview()) {
            handleArchReview(options.getReviewPath());
            return;
        }

        if (options.getAsk() != null) {
            askOnce(options.getAsk());
            return;
        }

        printBanner();
        repl();
    }

    /** 只打印静态分析事实，不调用模型。 */
    private void runScanOnly(String pathArg) {
        Path root =
                (pathArg == null || pathArg.isBlank())
                        ? factory.projectRoot()
                        : Path.of(pathArg).toAbsolutePath().normalize();
        if (!Files.isDirectory(root)) {
            System.err.println("✖ 目录不存在：" + root);
            System.exit(1);
            return;
        }
        try {
            ArchitectureAnalyzer.Result result = ArchitectureAnalyzer.analyze(root);
            System.out.println(result.render());
            Path report = result.writeReport(factory.workspaceDir().resolve("reports"));
            System.out.println("报告已保存：" + report);
            System.exit(result.findings().isEmpty() ? 0 : 1);
        } catch (Exception e) {
            System.err.println("✖ 静态分析失败：" + e.getMessage());
            System.exit(1);
        }
    }



    // ------------------------------------------------------------------ REPL

    private void repl() {
        while (true) {
            String line;
            try {
                line = reader.readLine(prompt());
            } catch (UserInterruptException e) {
                interruptAgent();
                continue;
            } catch (EndOfFileException e) {
                renderer.system("再见，继续加油 👋");
                return;
            }
            if (line == null) {
                renderer.system("再见，继续加油 👋");
                return;
            }
            String trimmed = line.trim();
            if (trimmed.isEmpty()) {
                continue;
            }
            if (SlashCommands.isCommand(trimmed)) {
                if (!handleCommand(trimmed)) {
                    return;
                }
                continue;
            }
            ask(trimmed);
        }
    }

    private String prompt() {
        return color
                ? new org.jline.utils.AttributedString(
                                "你 ", AttributedStyle.DEFAULT.foreground(AttributedStyle.GREEN).bold())
                        .toAnsi()
                        + new org.jline.utils.AttributedString("› ", AttributedStyle.DEFAULT.faint())
                                .toAnsi()
                : "你 > ";
    }

    private void interruptAgent() {
        if (agent != null) {
            agent.interrupt();
        }
        renderer.system("（已中断当前回答）");
    }

    /** 惰性创建 Agent；失败时打印友好提示并返回 false。 */
    private boolean ensureAgent() {
        if (this.agent != null) {
            return true;
        }
        try {
            this.agent = factory.create();
            return true;
        } catch (DevMentorConfigException e) {
            renderer.error(e.getMessage());
            renderer.system("提示：直接用 /login 登录厂商并输入 API Key，也可以设置环境变量后重启。");
            return false;
        } catch (RuntimeException e) {
            // 延迟 bean 初始化时异常可能被 Spring 包一层
            Throwable cause = e;
            while (cause != null && !(cause instanceof DevMentorConfigException)) {
                cause = cause.getCause();
            }
            if (cause instanceof DevMentorConfigException config) {
                renderer.error(config.getMessage());
                renderer.system("提示：直接用 /login 登录厂商并输入 API Key，也可以设置环境变量后重启。");
            } else {
                renderer.error("Agent 初始化失败：" + rootMessage(e));
            }
            return false;
        }
    }

    // ------------------------------------------------------------------ login

    /**
     * {@code /login}：先选厂商，再输入 Key，保存后立刻重建 Agent。
     *
     * <p>Key 用 JLine 的 {@link org.jline.reader.MaskingCallback} 掩码输入，避免明文留在
     * 屏幕上或被终端滚动缓冲记住。输入为空即取消。
     */
    private void handleLogin() {
        renderer.system(ProviderCatalog.menu());
        String choice = readQuietly("厂商序号 › ");
        if (choice == null || choice.isBlank()) {
            renderer.system("已取消。");
            return;
        }
        int id;
        try {
            id = Integer.parseInt(choice.trim());
        } catch (NumberFormatException e) {
            renderer.error("请输入序号（1-" + ProviderCatalog.PROVIDERS.size() + "）。");
            return;
        }
        ProviderCatalog.Provider provider = ProviderCatalog.byId(id);
        if (provider == null) {
            renderer.error("没有序号 " + id + " 对应的厂商。");
            return;
        }

        // 本地 Ollama 不需要 Key：配好地址直接切换。
        if (!ProviderCatalog.requiresKey(provider)) {
            applyProvider(provider, "");
            renderer.success("已切换到 " + provider.label() + "（无需 API Key）。");
            return;
        }

        renderer.system("厂商：" + provider.label());
        renderer.system("获取 Key：" + provider.hint());
        String key = readMasked("API Key › ");
        if (key == null || key.isBlank()) {
            renderer.system("已取消，未保存任何凭据。");
            return;
        }
        key = key.trim();

        try {
            credentialStore.save(provider.provider(), key);
            renderer.success("凭据已保存到 " + credentialStore.file());
        } catch (Exception e) {
            renderer.error("保存凭据失败：" + e.getMessage());
            return;
        }

        applyProvider(provider, key);
        renderer.success("已登录 " + provider.label() + "，模型：" + props.getModelId());
        renderer.system("现在可以开始提问了。");
    }

    /** 把选定的厂商写成配置，并重建 Agent 让新凭据立刻生效。 */
    private void applyProvider(ProviderCatalog.Provider provider, String apiKey) {
        props.setModelId(provider.provider() + ":" + provider.defaultModel());
        props.setBaseUrl(provider.defaultBaseUrl());
        props.setApiKey(apiKey);
        resetAgent();
    }

    /**
     * 丢掉当前 Agent，下次提问时按新配置重建。
     *
     * <p>模型与权限上下文都在 Agent 构建期绑定，改 provider 只能重建；会话 id 不变，
     * 因此新旧 Agent 指向同一份持久化状态。
     */
    private void resetAgent() {
        if (agent != null) {
            try {
                agent.close();
            } catch (Exception ignored) {
                // 关闭旧 Agent 失败不影响新建
            }
            agent = null;
        }
    }

    /** {@code /logout}：清除已保存的 Key。 */
    private void handleLogout(String providerArg) {
        java.util.Map<String, String> saved = credentialStore.load();
        if (saved.isEmpty()) {
            renderer.system("没有已保存的凭据。");
            return;
        }
        if (providerArg == null) {
            // 不带参数：清除当前模型对应的厂商，这是最常见的意图。
            String provider = currentProvider();
            if (provider != null && saved.containsKey(provider)) {
                removeProvider(provider);
                return;
            }
            StringBuilder sb = new StringBuilder("已保存凭据的厂商：\n");
            saved.forEach((p, k) -> sb.append("  ").append(p).append("  ").append(mask(k)).append('\n'));
            sb.append("\n用 /logout <厂商> 清除，例如 /logout openai。");
            renderer.system(sb.toString());
            return;
        }
        String provider = providerArg.toLowerCase(Locale.ROOT);
        ProviderCatalog.Provider known = ProviderCatalog.byProvider(provider);
        String name = known == null ? provider : known.provider();
        if (!saved.containsKey(name)) {
            renderer.error("没有为 " + name + " 保存凭据。");
            return;
        }
        removeProvider(name);
    }

    /** 删除指定 provider 的凭据并重建 Agent，让新状态立刻生效。 */
    private void removeProvider(String provider) {
        try {
            credentialStore.remove(provider);
            props.setApiKey("");
            resetAgent();
            renderer.success("已清除 " + provider + " 的凭据。输入 /login 可重新登录。");
        } catch (Exception e) {
            renderer.error("清除失败：" + e.getMessage());
        }
    }

    /** 当前模型 id 里的 provider 前缀；取不到时返回 {@code null}。 */
    private String currentProvider() {
        String modelId = props.getModelId();
        if (modelId == null) {
            return null;
        }
        int idx = modelId.indexOf(':');
        return idx > 0 ? modelId.substring(0, idx).toLowerCase(Locale.ROOT) : null;
    }

    /** 展示用：只露首尾几位。 */
    static String mask(String key) {
        if (key == null || key.length() <= 8) {
            return "****";
        }
        return key.substring(0, 4) + "…" + key.substring(key.length() - 4);
    }

    /** 安静读一行（不回显额外提示）。取消返回 null。 */
    private String readQuietly(String promptText) {
        try {
            return reader.readLine(promptText);
        } catch (Exception e) {
            return null;
        }
    }

    /**
     * 掩码读一行：屏幕上显示 {@code *}，且不写入历史记录。
     *
     * <p>{@link org.jline.reader.MaskingCallback#history(String)} 返回空串，Key 就不会被
     * 写进 {@code ~/.devmentor/history}——否则明文密钥会留在磁盘上。
     *
     * <p>非 TTY（管道、重定向）时 JLine 的掩码重绘会反复刷屏，此时退回普通读取：
     * 既然没有终端，屏幕上本来也看不到任何东西。
     */
    private String readMasked(String promptText) {
        if (!isInteractive()) {
            renderer.system(promptText + "（非交互输入，不回显）");
            return readQuietly("");
        }
        try {
            return reader.readLine(
                    promptText,
                    null,
                    new org.jline.reader.MaskingCallback() {
                        @Override
                        public String display(String line) {
                            return "*".repeat(line == null ? 0 : line.length());
                        }

                        @Override
                        public String history(String line) {
                            return ""; // 不记录到历史，避免明文落盘
                        }
                    },
                    null);
        } catch (Exception e) {
            return null;
        }
    }

    /** 当前是否连着真实终端。管道/重定向时为 {@code false}。 */
    private boolean isInteractive() {
        return terminal != null && !"dumb".equals(terminal.getType());
    }

    // --------------------------------------------------------------- commands

    /** @return false 表示应退出 */
    private boolean handleCommand(String line) {
        SlashCommands.Parsed parsed = SlashCommands.parse(line);
        if (parsed == null) {
            renderer.error("命令格式不对，输入 /help 查看用法。");
            return true;
        }
        switch (parsed.name()) {
            case "quit", "exit" -> {
                renderer.system("再见，继续加油 👋");
                return false;
            }
            case "help" -> {
                renderer.system(SlashCommands.helpText());
                return true;
            }
            case "new" -> {
                String id = session.startNew(parsed.arg(0));
                renderer.success("已开启新会话：" + id);
                return true;
            }
            case "reset" -> {
                if (!ensureAgent()) return true;
                agent.clearContext(session.runtimeContext());
                renderer.success("当前会话上下文已清空。");
                return true;
            }
            case "arch" -> {
                handleArchReview(parsed.arg(0));
                return true;
            }
            case "mode" -> {
                String target = parsed.arg(0);
                if (target == null) {
                    renderer.system("当前权限档位：" + PermissionProfiles.describe(props.getPermissionMode()));
                    return true;
                }
                try {
                    PermissionProfiles.of(target);
                } catch (IllegalArgumentException e) {
                    renderer.error(e.getMessage());
                    return true;
                }
                if (!ensureAgent()) return true;
                props.setPermissionMode(target);
                // setPermissionMode 会保留已安装的 ASK 规则，只切换模式；
                // interactive 对应 ACCEPT_EDITS（只读放行、写操作询问）。
                agent.setPermissionMode(
                        session.getUserId(), session.getSessionId(), modeOf(target));
                renderer.success("权限档位已切换为 " + PermissionProfiles.describe(target));
                return true;
            }
            case "plan" -> {
                if (!ensureAgent()) return true;
                String target = parsed.arg(0);
                boolean on = agent.isPlanModeActive(session.runtimeContext());
                if (target == null) {
                    renderer.system("plan 模式当前：" + (on ? "开启" : "关闭"));
                    return true;
                }
                boolean want = "on".equalsIgnoreCase(target) || "true".equalsIgnoreCase(target);
                if (want) {
                    agent.enterPlanMode(session.runtimeContext());
                } else {
                    agent.exitPlanMode(session.runtimeContext());
                }
                renderer.success("plan 模式已" + (want ? "开启（只读设计阶段）" : "关闭"));
                return true;
            }
            case "lesson" -> {
                handleLesson(parsed.arg(0));
                return true;
            }
            case "progress" -> {
                askQuietly("请用 progress_read 工具读出我的学习进度，并给一句简短点评。");
                return true;
            }
            case "lang" -> {
                String lang = parsed.arg(0);
                if (lang == null || !(lang.equalsIgnoreCase("zh") || lang.equalsIgnoreCase("en"))) {
                    renderer.system("用法：/lang <zh|en>");
                    return true;
                }
                updateLanguage(lang.toLowerCase(Locale.ROOT));
                return true;
            }
            case "login" -> {
                handleLogin();
                return true;
            }
            case "logout" -> {
                handleLogout(parsed.arg(0));
                return true;
            }
            case "model" -> {
                String id = parsed.arg(0);
                if (id == null) {
                    renderer.system("当前模型：" + props.getModelId() + "（用 /model <id> 切换）");
                    return true;
                }
                props.setModelId(id);
                renderer.system(
                        "已记录模型 " + id + "。为保持会话状态一致，请重启程序后生效。");
                return true;
            }
            case "tools" -> {
                if (!ensureAgent()) return true;
                renderer.system("可用工具：\n  " + String.join("\n  ", agent.getToolkit().getToolNames().stream().sorted().toList()));
                return true;
            }
            case "workspace" -> {
                renderer.system(
                        "工作区：" + factory.workspaceDir() + "\n代码目录：" + factory.projectRoot()
                                + "\n状态目录：" + factory.stateDir());
                return true;
            }
            case "session" -> {
                renderer.system(
                        "用户：" + session.getUserId() + "\n会话：" + session.getSessionId()
                                + "\n模型：" + props.getModelId()
                                + "\n权限：" + PermissionProfiles.describe(props.getPermissionMode()));
                return true;
            }
            case "verbose" -> {
                verbose = !verbose;
                rebuildRenderer();
                renderer.system("工具输出：" + (verbose ? "全量" : "摘要"));
                return true;
            }
            case "think" -> {
                showThinking = !showThinking;
                rebuildRenderer();
                renderer.system("推理过程：" + (showThinking ? "显示" : "隐藏"));
                return true;
            }
            default -> {
                renderer.error("未知命令 /" + parsed.name() + "，输入 /help 查看用法。");
                return true;
            }
        }
    }

    /**
     * 架构评审：先跑确定性静态分析把事实摆出来，再让模型基于事实给判断。
     *
     * <p>直接打印分析结果是有意的——用户应当先看到「机器测得的事实」，再看「模型的解读」，
     * 这样他能分辨哪些是证据、哪些是建议。
     */
    private void handleArchReview(String pathArg) {
        Path root =
                (pathArg == null || pathArg.isBlank())
                        ? factory.projectRoot()
                        : Path.of(pathArg).toAbsolutePath().normalize();
        if (!Files.isDirectory(root)) {
            renderer.error("目录不存在：" + root);
            return;
        }
        ArchitectureAnalyzer.Result result;
        try {
            result = ArchitectureAnalyzer.analyze(root);
        } catch (Exception e) {
            renderer.error("静态分析失败：" + e.getMessage());
            return;
        }
        if (result.isEmpty()) {
            renderer.error("在 " + root + " 下没有找到 .java 文件。");
            return;
        }

        // 先把确定性事实打给用户看
        renderer.system(result.render());
        try {
            Path report = result.writeReport(factory.workspaceDir().resolve("reports"));
            renderer.success("事实报告已保存：" + report);
        } catch (Exception e) {
            renderer.system("（报告落盘失败：" + e.getMessage() + "）");
        }

        long high = result.countOf(ArchFinding.Severity.HIGH);
        long medium = result.countOf(ArchFinding.Severity.MEDIUM);
        String prompt =
                String.format(
                        "我刚对一个 Java 项目做了静态分析，结果已经打印给你看了：共 %d 个源文件、%d 条规则命中（高 %d / 中 %d）。"
                                + "项目根目录是 %s。\n\n"
                                + "请基于这些事实做架构评审：\n"
                                + "1. 挑 3~5 个真正影响这个项目的问题，按「证据 / 影响 / 改法 / 顺序」四段写；\n"
                                + "2. 需要看具体代码时用 arch_read_source，需要看某个类时用 arch_file_profile 核实；\n"
                                + "3. 最后给一个按「影响÷成本」排序的优先级表；\n"
                                + "4. 不要泛泛而谈，每条都要能指回具体文件或数字。",
                        result.snapshot().fileCount(), result.findings().size(), high, medium, root);
        askQuietly(prompt);
    }

    /** 档位 → 权限模式；规则由初次安装的 PermissionContext 保留。 */
    private PermissionMode modeOf(String profile) {
        return switch (PermissionProfiles.normalize(profile)) {
            case PermissionProfiles.READ_ONLY -> PermissionMode.EXPLORE;
            case PermissionProfiles.FULL -> PermissionMode.BYPASS;
            default -> PermissionMode.ACCEPT_EDITS;
        };
    }

    private void handleLesson(String slug) {
        Path dir = factory.workspaceDir().resolve("curriculum");
        if (slug == null) {
            askQuietly("请用 curriculum_list 列出课程，并告诉我从哪一课开始比较合适。");
            return;
        }
        Path file = dir.resolve(slug.endsWith(".md") ? slug : slug + ".md");
        if (!Files.isRegularFile(file)) {
            renderer.error("没有找到课程 " + slug + "。用 /lesson 查看全部课程。");
            return;
        }
        try {
            String content = Files.readString(file, StandardCharsets.UTF_8);
            renderer.system(content);
            askQuietly("我刚读了课程《" + slug + "》，请带我过一遍重点，并出一道练习题。");
        } catch (Exception e) {
            renderer.error("读取课程失败：" + e.getMessage());
        }
    }

    private void updateLanguage(String lang) {
        Path prefs = factory.workspaceDir().resolve("preferences.md");
        try {
            String content = Files.isRegularFile(prefs) ? Files.readString(prefs, StandardCharsets.UTF_8) : "";
            String updated = content.replaceAll("(?m)^(- 语言[：:]\\s*).*$", "$1" + ("en".equals(lang) ? "英文" : "中文"));
            if (updated.equals(content)) {
                updated = content + System.lineSeparator() + "- 语言：" + ("en".equals(lang) ? "英文" : "中文")
                        + System.lineSeparator();
            }
            Files.createDirectories(prefs.getParent());
            Files.writeString(prefs, updated, StandardCharsets.UTF_8);
            props.setLanguage(lang);
            renderer.success("讲解语言已切换为 " + ("en".equals(lang) ? "英文" : "中文") + "（下一轮生效）");
        } catch (Exception e) {
            renderer.error("更新语言偏好失败：" + e.getMessage());
        }
    }

    private void rebuildRenderer() {
        renderer = new TerminalRenderer(terminal.writer(), color, showThinking, verbose);
    }

    // ------------------------------------------------------------- agent turn

    private void askOnce(String text) {
        ask(text);
        renderer.finishTurn();
    }

    private void askQuietly(String text) {
        ask(text);
    }

    /** 跑一轮对话，处理流式事件与 HITL 确认。 */
    private void ask(String text) {
        if (!ensureAgent()) {
            return; // 创建失败，已提示用户
        }
        RuntimeContext ctx = session.runtimeContext();
        AtomicReference<List<ToolUseBlock>> pending = new AtomicReference<>(List.of());
        AtomicReference<String> failure = new AtomicReference<>();

        try {
            agent.streamEvents(new UserMessage(text), ctx)
                    .doOnNext(
                            event -> {
                                renderer.render(event);
                                if (event.getType() == AgentEventType.REQUIRE_USER_CONFIRM
                                        && event instanceof RequireUserConfirmEvent confirm) {
                                    pending.set(confirm.getToolCalls());
                                }
                            })
                    .doOnError(e -> failure.set(rootMessage(e)))
                    .onErrorResume(e -> reactor.core.publisher.Flux.empty())
                    .blockLast();
        } catch (Exception e) {
            failure.set(rootMessage(e));
        }

        if (failure.get() != null) {
            renderer.error(friendly(failure.get()));
        }
        renderer.finishTurn();

        List<ToolUseBlock> asking = pending.get();
        if (asking != null && !asking.isEmpty()) {
            resolveConfirmations(asking);
        }
    }

    /** 逐个询问待确认的工具调用，然后把结果回送给 Agent 继续执行。 */
    private void resolveConfirmations(List<ToolUseBlock> asking) {
        List<ConfirmResult> results = new ArrayList<>();
        for (ToolUseBlock toolCall : asking) {
            renderer.detail(
                    "需要确认：" + toolCall.getName(),
                    TerminalRenderer.formatToolInput(toolCall.getInput()));
            boolean approved = confirm("是否允许执行？[y/N] ");
            results.add(
                    approved
                            ? new ConfirmResult(true, toolCall)
                            : new ConfirmResult(false, toolCall, null, "用户拒绝了该操作"));
        }

        Map<String, Object> metadata = new HashMap<>();
        metadata.put(Msg.METADATA_CONFIRM_RESULTS, results);
        UserMessage resume =
                UserMessage.builder().metadata(metadata).textContent("（确认结果）").build();

        try {
            agent.streamEvents(resume, session.runtimeContext())
                    .doOnNext(renderer::render)
                    .onErrorResume(
                            e -> {
                                renderer.error(friendly(rootMessage(e)));
                                return reactor.core.publisher.Flux.empty();
                            })
                    .blockLast();
        } catch (Exception e) {
            renderer.error(friendly(rootMessage(e)));
        }
        renderer.finishTurn();
    }

    private boolean confirm(String promptText) {
        try {
            String answer = reader.readLine(promptText);
            return answer != null && answer.trim().toLowerCase(Locale.ROOT).startsWith("y");
        } catch (Exception e) {
            return false;
        }
    }

    // ------------------------------------------------------------------ setup

    private LineReader buildLineReader() {
        Path historyFile = factory.workspaceDir().getParent().resolve("history");
        try {
            if (historyFile.getParent() != null) {
                Files.createDirectories(historyFile.getParent());
            }
        } catch (Exception ignored) {
            // 历史文件不可写不影响使用
        }
        DefaultHistory history = new DefaultHistory();
        SlashCommandCompleter completer = new SlashCommandCompleter();
        LineReaderBuilder builder =
                LineReaderBuilder.builder()
                        .terminal(terminal)
                        .appName("devmentor")
                        .history(history)
                        .parser(new DefaultParser())
                        .completer(completer);
        LineReader lineReader = builder.build();
        lineReader.setVariable(LineReader.HISTORY_FILE, historyFile);

        // 输入 "/" 就立刻列出候选，不必先按 Tab。
        lineReader.setOpt(LineReader.Option.AUTO_LIST);
        // AUTO_MENU_LIST 让候选按"描述列"排版，读起来像一张菜单。
        lineReader.setOpt(LineReader.Option.AUTO_MENU_LIST);
        // 注意：不开 AUTO_MENU。它会在候选唯一时自动改写输入，
        // 在非 TTY（管道/重定向）下会把 /quit 之类改坏成 /archquit。
        // 自动弹菜单统一由下面的 installAutoMenuOnSlash 负责。
        // 多候选时进入可交互的菜单循环（Tab 下一个、Shift+Tab 上一个）。
        lineReader.setOpt(LineReader.Option.MENU_COMPLETE);
        // 候选多于一屏时滚动显示。
        lineReader.setVariable(LineReader.LIST_MAX, 200);
        lineReader.setVariable(LineReader.MENU_LIST_MAX, 200);

        styleCompletionMenu(lineReader);
        bindMenuArrowKeys(lineReader);
        // 只在真实终端里接管打字补全。管道/重定向时 JLine 会逐字符喂入，
        // 弹菜单会把后续字符当导航键吃掉（例如 /quit 变成 /archquit）。
        if (isInteractive()) {
            installAutoMenuOnSlash(lineReader, completer);
        }
        return lineReader;
    }

    /**
     * 输入 {@code /} 或继续输入命令前缀时，主动弹出候选菜单。
     *
     * <p>JLine 的 {@code AUTO_LIST} 只在 <b>按 Tab 触发的 doComplete 内部</b>生效，打字过程中
     * 根本不会调用 completer（{@code selfInsert} 只负责插入字符）。所以"输入斜杠就出菜单"必须
     * 自己接管 {@code self-insert}：插入字符后，若当前行以 {@code /} 开头且还没有空格，
     * 就主动调一次补全 widget。
     *
     * <p>只在斜杠命令场景触发，普通提问打字时完全不干预。
     */
    private static void installAutoMenuOnSlash(
            LineReader lineReader, SlashCommandCompleter completer) {
        Widget original = lineReader.getWidgets().get(LineReader.SELF_INSERT);
        if (original == null) {
            return;
        }
        lineReader.getWidgets()
                .put(
                        LineReader.SELF_INSERT,
                        () -> {
                            String before = lineReader.getBuffer().toString();
                            int cursorBefore = lineReader.getBuffer().cursor();
                            original.apply();

                            String trimmed = lineReader.getBuffer().toString().stripLeading();
                            boolean typingCommand =
                                    trimmed.startsWith("/") && trimmed.indexOf(' ') < 0;
                            if (!typingCommand) {
                                return true;
                            }

                            // 只有候选不止一个时才进菜单，唯一候选直接补全更省事。
                            if (lineReader.getBuffer().toString().equals(before)) {
                                return true; // 没插入任何字符（如方向键），不重复触发
                            }
                            int matches = countCandidates(lineReader, completer);
                            // 只有多候选才弹菜单。唯一候选或零候选时绝不动输入——
                            // 否则会出现输入 /quit 被补成 /archquit 这类误伤。
                            if (matches > 1) {
                                lineReader.callWidget(LineReader.MENU_COMPLETE);
                            }
                            return true;
                        });
    }

    /**
     * 去掉候选菜单的洋红底色，改成不抢眼的样式。
     *
     * <p>JLine 默认 {@code LIST_BACKGROUND = "bg:bright-magenta"}、{@code SELECTION = "inverse"}，
     * 候选区会被整块刷成亮洋红并反色，在深色终端上非常刺眼。这里：
     * <ul>
     *   <li>背景设为 {@code bg:default}，跟随终端本色，不额外填充；
     *   <li>选中项只用<b>加粗 + 青绿前景</b>，不用反色块；
     *   <li>说明文字用暗色，作为次要信息。
     * </ul>
     * 保留 16 色以内的取值，确保老式 conhost 也能正确渲染。
     */
    private static void styleCompletionMenu(LineReader lineReader) {
        lineReader.setVariable(LineReader.COMPLETION_STYLE_LIST_BACKGROUND, "bg:default");
        lineReader.setVariable(LineReader.COMPLETION_STYLE_BACKGROUND, "bg:default");
        lineReader.setVariable(LineReader.COMPLETION_STYLE_LIST_SELECTION, "fg:cyan,bold");
        lineReader.setVariable(LineReader.COMPLETION_STYLE_SELECTION, "fg:cyan,bold");
        lineReader.setVariable(LineReader.COMPLETION_STYLE_LIST_STARTING, "fg:green");
        lineReader.setVariable(LineReader.COMPLETION_STYLE_STARTING, "fg:green");
        lineReader.setVariable(LineReader.COMPLETION_STYLE_LIST_DESCRIPTION, "fg:bright-black");
        lineReader.setVariable(LineReader.COMPLETION_STYLE_DESCRIPTION, "fg:bright-black");
    }

    /**
     * 给 JLine 的 {@code menu} keymap 补上上下方向键。
     *
     * <p>JLine 进入菜单循环后只处理 {@code menu} keymap 里的键，而它默认只绑了
     * Tab / Shift+Tab / Enter 三个。{@code doMenu()} 内部其实**已经实现**了
     * {@code menuSupport.up()} / {@code down()} 的分支（对应 UP_LINE_OR_HISTORY /
     * DOWN_LINE_OR_HISTORY），只是没绑键。这里把方向键接上去，就能用上下键在候选中移动、
     * 用 Enter 确认——与 Claude Code 的手感一致。
     */
    private static void bindMenuArrowKeys(LineReader lineReader) {
        KeyMap<Binding> menu = lineReader.getKeyMaps().get(LineReader.MENU);
        if (menu == null) {
            return; // 没有 menu keymap 时保持 JLine 默认行为
        }
        Terminal term = lineReader.getTerminal();
        menu.bind(new Reference(LineReader.UP_LINE_OR_HISTORY),
                KeyMap.key(term, InfoCmp.Capability.key_up));
        menu.bind(new Reference(LineReader.DOWN_LINE_OR_HISTORY),
                KeyMap.key(term, InfoCmp.Capability.key_down));
    }

    /** 当前行能补出多少个候选（用于决定是否进菜单）。 */
    private static int countCandidates(LineReader lineReader, SlashCommandCompleter completer) {
        try {
            List<Candidate> found = new ArrayList<>();
            completer.complete(
                    lineReader,
                    lineReader.getParser()
                            .parse(
                                    lineReader.getBuffer().toString(),
                                    lineReader.getBuffer().cursor()),
                    found);
            return found.size();
        } catch (Exception | Error e) {
            return 0; // 任何异常都退回"不弹菜单"，不能打断输入
        }
    }

    private boolean supportsColor() {
        if (System.getenv("NO_COLOR") != null) {
            return false;
        }
        String type = terminal.getType();
        return type != null && !"dumb".equals(type);
    }

    private void printBanner() {
        PrintWriter out = terminal.writer();
        String title = "DevMentor · Java 编程导师";
        out.println(renderer.paint("┌" + "─".repeat(56) + "┐", AttributedStyle.DEFAULT.faint()));
        out.println(
                renderer.paint(
                        "│ " + pad(title, 54) + " │",
                        AttributedStyle.DEFAULT.foreground(AttributedStyle.CYAN).bold()));
        out.println(renderer.paint("└" + "─".repeat(56) + "┘", AttributedStyle.DEFAULT.faint()));
        out.println("  模型     " + props.getModelId());
        out.println("  凭据     " + credentialStatus());
        out.println("  会话     " + session.getSessionId());
        out.println("  工作区   " + factory.workspaceDir());
        out.println("  代码目录 " + factory.projectRoot());
        out.println("  权限     " + PermissionProfiles.describe(props.getPermissionMode()));
        out.println();
        out.println(renderer.paint("  直接提问，或输入 /help 查看命令。", AttributedStyle.DEFAULT.faint()));
        out.println();
        out.flush();
    }

    /** 一行说明当前凭据来源，让用户一眼看出"能不能用"以及 key 从哪来。 */
    private String credentialStatus() {
        String modelId = props.getModelId();
        int idx = modelId.indexOf(':');
        String provider = idx > 0 ? modelId.substring(0, idx).toLowerCase(Locale.ROOT) : "";
        if (props.getApiKey() != null && !props.getApiKey().isBlank()) {
            return "已提供（" + mask(props.getApiKey()) + "）";
        }
        String saved = credentialStore.find(provider);
        if (saved != null && !saved.isBlank()) {
            return "已登录 " + provider + "（" + mask(saved) + "）";
        }
        if ("ollama".equals(provider)) {
            return "无需 Key（本地 Ollama）";
        }
        return "未登录 — 输入 /login 选择厂商并填入 API Key";
    }

    /**
     * 按**终端显示宽度**补空格。中文是全角字符，占两列，用 {@code String#length()} 会把
     * 边框撑歪。
     */
    private static String pad(String text, int width) {
        int len = displayWidth(text);
        if (len >= width) {
            return text;
        }
        return text + " ".repeat(width - len);
    }

    /** 估算显示宽度：CJK / 全角标点算 2 列，其余算 1 列。 */
    static int displayWidth(String text) {
        int width = 0;
        for (int i = 0; i < text.length(); i++) {
            char c = text.charAt(i);
            width += isWide(c) ? 2 : 1;
        }
        return width;
    }

    private static boolean isWide(char c) {
        return (c >= 0x1100 && c <= 0x115F)
                || (c >= 0x2E80 && c <= 0xA4CF)
                || (c >= 0xAC00 && c <= 0xD7A3)
                || (c >= 0xF900 && c <= 0xFAFF)
                || (c >= 0xFE30 && c <= 0xFE6F)
                || (c >= 0xFF00 && c <= 0xFF60)
                || (c >= 0xFFE0 && c <= 0xFFE6);
    }

    private static String rootMessage(Throwable t) {
        Throwable cur = t;
        while (cur.getCause() != null && cur.getCause() != cur) {
            cur = cur.getCause();
        }
        String msg = cur.getMessage();
        return msg == null || msg.isBlank() ? cur.getClass().getSimpleName() : msg;
    }

    /** 把常见失败翻译成可操作的中文提示。 */
    static String friendly(String message) {
        if (message == null) {
            return "未知错误。";
        }
        String lower = message.toLowerCase(Locale.ROOT);
        if (lower.contains("401") || lower.contains("unauthorized") || lower.contains("invalid api key")) {
            return "模型鉴权失败（401）：请检查 OPENROUTER_API_KEY 是否正确。\n" + message;
        }
        if (lower.contains("402") || lower.contains("insufficient")) {
            return "账户额度不足（402）：免费模型可能有配额限制，可换模型或稍后再试。\n" + message;
        }
        if (lower.contains("429") || lower.contains("rate limit")) {
            return "触发限流（429）：免费模型请求过于频繁，等几秒重试，或用 /model 换一个模型。\n" + message;
        }
        if (lower.contains("403") || lower.contains("forbidden")) {
            return "模型拒绝服务（403）：该模型可能已下线或需要额外授权，用 /model 换一个。\n" + message;
        }
        if (lower.contains("timeout") || lower.contains("timed out")) {
            return "请求超时：网络或模型响应过慢，可以重试或换模型。\n" + message;
        }
        return message;
    }

    /** 供测试使用：注入已构建的依赖。 */
    void setAgent(HarnessAgent agent) {
        this.agent = agent;
    }

    void setSession(MentorSession session) {
        this.session = session;
    }
}