package dre4m1nd.devmentor.config;

import java.util.List;

/**
 * 内置的模型厂商目录：{@code /login} 用它来列出可选厂商，并为每个厂商准备默认 baseUrl
 * 与推荐模型。
 *
 * <p>目录是**静态清单**而不是反射扫描：这里只放确认过 {@code provider:model} 前缀能被
 * {@code ModelRegistry} 解析的厂商，避免列出无法使用的选项。
 */
public final class ProviderCatalog {

    private ProviderCatalog() {}

    /**
     * 一个厂商。
     *
     * @param id 菜单序号（从 1 开始）
     * @param label 显示名
     * @param provider {@code provider:model} 里的 provider 前缀
     * @param envVar 该厂商的标准环境变量名，用于找不到 Key 时的提示
     * @param defaultBaseUrl 默认网关地址；为空表示用 SDK 默认
     * @param defaultModel 该厂商的默认模型
     * @param hint 获取 Key 的地址或说明
     */
    public record Provider(
            int id,
            String label,
            String provider,
            String envVar,
            String defaultBaseUrl,
            String defaultModel,
            String hint) {}

    /**
     * 全部内置厂商。
     *
     * <p>OpenRouter 放在第一项：它提供免费模型，是「不花钱就能跑起来」的默认路径。
     */
    public static final List<Provider> PROVIDERS =
            List.of(
                    new Provider(
                            1,
                            "OpenRouter（免费模型，推荐）",
                            "openai",
                            "OPENROUTER_API_KEY",
                            "https://openrouter.ai/api/v1",
                            "minimax/minimax-m3.1-flash:free",
                            "https://openrouter.ai/keys"),
                    new Provider(
                            2,
                            "DeepSeek",
                            "deepseek",
                            "DEEPSEEK_API_KEY",
                            "",
                            "deepseek-chat",
                            "https://platform.deepseek.com/api_keys"),
                    new Provider(
                            3,
                            "阿里云百炼 DashScope",
                            "dashscope",
                            "DASHSCOPE_API_KEY",
                            "",
                            "qwen-plus",
                            "https://bailian.console.aliyun.com/"),
                    new Provider(
                            4,
                            "OpenAI",
                            "openai",
                            "OPENAI_API_KEY",
                            "https://api.openai.com/v1",
                            "gpt-4.1-mini",
                            "https://platform.openai.com/api-keys"),
                    new Provider(
                            5,
                            "Anthropic Claude",
                            "anthropic",
                            "ANTHROPIC_API_KEY",
                            "",
                            "claude-sonnet-4-20250514",
                            "https://console.anthropic.com/settings/keys"),
                    new Provider(
                            6,
                            "本地 Ollama（无需 Key）",
                            "ollama",
                            "",
                            "http://localhost:11434",
                            "qwen2.5-coder",
                            "https://ollama.com/download"));

    /** 按菜单序号查找。 */
    public static Provider byId(int id) {
        return PROVIDERS.stream().filter(p -> p.id() == id).findFirst().orElse(null);
    }

    /** 按 provider 前缀查找（返回第一个匹配）。 */
    public static Provider byProvider(String provider) {
        if (provider == null) {
            return null;
        }
        String p = provider.toLowerCase(java.util.Locale.ROOT);
        return PROVIDERS.stream().filter(x -> x.provider().equals(p)).findFirst().orElse(null);
    }

    /** 该厂商是否需要 API Key（本地 Ollama 不需要）。 */
    public static boolean requiresKey(Provider p) {
        return p != null && !p.envVar().isEmpty();
    }

    /** 渲染成菜单文本。 */
    public static String menu() {
        StringBuilder sb = new StringBuilder("选择模型厂商：\n");
        for (Provider p : PROVIDERS) {
            sb.append(String.format("  %d) %s%n", p.id(), p.label()));
        }
        sb.append("\n输入序号，或直接回车取消。");
        return sb.toString();
    }
}
