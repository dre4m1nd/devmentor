package dre4m1nd.devmentor.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

/**
 * 全部可配置项，前缀 {@code devmentor}。
 *
 * <p>所有字段都有安全默认值，因此不做任何配置也能直接启动（只要环境里有模型 API Key）。
 * 密钥只从环境变量读取，{@code application.yaml} 里写的是 {@code ${OPENROUTER_API_KEY:}}，
 * 不会把明文提交进仓库。
 */
@Component
@ConfigurationProperties(prefix = "devmentor")
public class MentorProperties {

    /** provider:model 形式，例如 {@code openai:minimax/minimax-m3.1-flash:free}。 */
    private String modelId = "openai:minimax/minimax-m3.1-flash:free";

    /** 模型 API Key；为空时按 provider 的标准环境变量回退。 */
    private String apiKey = "";

    /** 自定义网关地址，例如 OpenRouter 的 {@code https://openrouter.ai/api/v1}。 */
    private String baseUrl = "";

    /** 导师讲解语言：{@code zh} 或 {@code en}。 */
    private String language = "zh";

    /** 会话所属用户标识，参与 AgentState 的寻址。 */
    private String userId = "learner";

    /** 会话标识；为空时自动生成。 */
    private String sessionId = "";

    /** 工作区目录（AGENTS.md、课程、技能、记忆都在这里）。 */
    private String workspace = ".devmentor/workspace";

    /** 会话状态持久化目录。 */
    private String stateDir = ".devmentor/state";

    /** 用户代码目录；为空表示当前工作目录。智能体的文件工具会落到这里。 */
    private String projectRoot = "";

    /** 权限档位：{@code interactive} / {@code read-only} / {@code full}。 */
    private String permissionMode = "interactive";

    /** ReAct 循环最大迭代次数。 */
    private int maxIters = 24;

    /** 触发上下文压缩的消息条数阈值。 */
    private int maxHistoryMessages = 50;

    /** 是否开放宿主机 shell 工具（默认关闭）。 */
    private boolean enableShell = false;

    /** 是否启用 plan 模式工具。 */
    private boolean enablePlanMode = true;

    /** 是否允许智能体自行创建/修改技能。 */
    private boolean enableSkillManage = true;

    private Tools tools = new Tools();

    private Cli cli = new Cli();

    public String getModelId() {
        return modelId;
    }

    public void setModelId(String modelId) {
        this.modelId = modelId;
    }

    public String getApiKey() {
        return apiKey;
    }

    public void setApiKey(String apiKey) {
        this.apiKey = apiKey;
    }

    public String getBaseUrl() {
        return baseUrl;
    }

    public void setBaseUrl(String baseUrl) {
        this.baseUrl = baseUrl;
    }

    public String getLanguage() {
        return language;
    }

    public void setLanguage(String language) {
        this.language = language;
    }

    public String getUserId() {
        return userId;
    }

    public void setUserId(String userId) {
        this.userId = userId;
    }

    public String getSessionId() {
        return sessionId;
    }

    public void setSessionId(String sessionId) {
        this.sessionId = sessionId;
    }

    public String getWorkspace() {
        return workspace;
    }

    public void setWorkspace(String workspace) {
        this.workspace = workspace;
    }

    public String getStateDir() {
        return stateDir;
    }

    public void setStateDir(String stateDir) {
        this.stateDir = stateDir;
    }

    public String getProjectRoot() {
        return projectRoot;
    }

    public void setProjectRoot(String projectRoot) {
        this.projectRoot = projectRoot;
    }

    public String getPermissionMode() {
        return permissionMode;
    }

    public void setPermissionMode(String permissionMode) {
        this.permissionMode = permissionMode;
    }

    public int getMaxIters() {
        return maxIters;
    }

    public void setMaxIters(int maxIters) {
        this.maxIters = maxIters;
    }

    public int getMaxHistoryMessages() {
        return maxHistoryMessages;
    }

    public void setMaxHistoryMessages(int maxHistoryMessages) {
        this.maxHistoryMessages = maxHistoryMessages;
    }

    public boolean isEnableShell() {
        return enableShell;
    }

    public void setEnableShell(boolean enableShell) {
        this.enableShell = enableShell;
    }

    public boolean isEnablePlanMode() {
        return enablePlanMode;
    }

    public void setEnablePlanMode(boolean enablePlanMode) {
        this.enablePlanMode = enablePlanMode;
    }

    public boolean isEnableSkillManage() {
        return enableSkillManage;
    }

    public void setEnableSkillManage(boolean enableSkillManage) {
        this.enableSkillManage = enableSkillManage;
    }

    public Tools getTools() {
        return tools;
    }

    public void setTools(Tools tools) {
        this.tools = tools;
    }

    public Cli getCli() {
        return cli;
    }

    public void setCli(Cli cli) {
        this.cli = cli;
    }

    /** {@code devmentor.tools.*} */
    public static class Tools {

        private JavaRun javaRun = new JavaRun();

        private Arch arch = new Arch();

        public JavaRun getJavaRun() {
            return javaRun;
        }

        public void setJavaRun(JavaRun javaRun) {
            this.javaRun = javaRun;
        }

        public Arch getArch() {
            return arch;
        }

        public void setArch(Arch arch) {
            this.arch = arch;
        }
    }

    /** {@code devmentor.tools.arch.*}：项目架构评审工具。 */
    public static class Arch {

        private boolean enabled = true;

        public boolean isEnabled() {
            return enabled;
        }

        public void setEnabled(boolean enabled) {
            this.enabled = enabled;
        }
    }

    /** {@code devmentor.tools.java-run.*}：Java 片段编译/运行工具。 */
    public static class JavaRun {

        private boolean enabled = true;

        private int timeoutSeconds = 10;

        private int maxSourceChars = 20000;

        public boolean isEnabled() {
            return enabled;
        }

        public void setEnabled(boolean enabled) {
            this.enabled = enabled;
        }

        public int getTimeoutSeconds() {
            return timeoutSeconds;
        }

        public void setTimeoutSeconds(int timeoutSeconds) {
            this.timeoutSeconds = timeoutSeconds;
        }

        public int getMaxSourceChars() {
            return maxSourceChars;
        }

        public void setMaxSourceChars(int maxSourceChars) {
            this.maxSourceChars = maxSourceChars;
        }
    }

    /** {@code devmentor.cli.*} */
    public static class Cli {

        private boolean enabled = true;

        public boolean isEnabled() {
            return enabled;
        }

        public void setEnabled(boolean enabled) {
            this.enabled = enabled;
        }
    }
}
