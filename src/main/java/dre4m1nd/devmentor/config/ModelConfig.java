package dre4m1nd.devmentor.config;

import io.agentscope.core.model.Model;
import io.agentscope.core.model.ModelCreationContext;
import io.agentscope.core.model.ModelRegistry;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * 构造对话模型。
 *
 * <p>用 {@link ModelRegistry} 解析 {@code provider:model} 形式的 id，从而同时支持
 * {@code openai:}（含 OpenRouter 等兼容网关）、{@code deepseek:}、{@code dashscope:}、
 * {@code anthropic:}、{@code ollama:} 等，切换 provider 只需改配置。
 */
@Configuration(proxyBeanMethods = false)
public class ModelConfig {

    private static final Logger log = LoggerFactory.getLogger(ModelConfig.class);

    private final MentorProperties props;

    public ModelConfig(MentorProperties props) {
        this.props = props;
    }

    /**
     * 模型 bean 延迟创建：没有 API Key 时上下文仍能启动，{@code --self-check} 因此可以
     * 只做装配检查而不必联网。真正需要模型时才会抛出 {@link DevMentorConfigException}。
     */
    @Bean
    @org.springframework.context.annotation.Lazy
    public Model mentorModel() {
        String modelId = props.getModelId();
        if (modelId == null || modelId.isBlank()) {
            throw new DevMentorConfigException(
                    "未配置模型：请设置 devmentor.model-id（形如 provider:model）。");
        }
        if (modelId.indexOf(':') < 0) {
            throw new DevMentorConfigException(
                    "模型 id \"" + modelId + "\" 缺少 provider 前缀。"
                            + "请写成 provider:model，例如 openai:minimax/minimax-m3.1-flash:free");
        }

        String apiKey = blankToNull(props.getApiKey());
        String baseUrl = blankToNull(props.getBaseUrl());
        if (apiKey == null && requiresApiKey(modelId)) {
            throw new DevMentorConfigException(
                    missingKeyMessage(modelId));
        }

        ModelCreationContext.Builder ctx =
                ModelCreationContext.builder().stream(Boolean.TRUE);
        if (apiKey != null) {
            ctx.apiKey(apiKey);
        }
        if (baseUrl != null) {
            ctx.baseUrl(baseUrl);
        }

        try {
            Model model = ModelRegistry.resolve(modelId, ctx.build());
            log.info("模型已就绪: {} (baseUrl={})", modelId, baseUrl == null ? "provider 默认" : baseUrl);
            return model;
        } catch (RuntimeException e) {
            throw new DevMentorConfigException(
                    "无法创建模型 \"" + modelId + "\"：" + rootMessage(e) + "\n" + missingKeyMessage(modelId),
                    e);
        }
    }

    private static boolean requiresApiKey(String modelId) {
        return !modelId.startsWith("ollama:");
    }

    private String missingKeyMessage(String modelId) {
        String provider = modelId.substring(0, Math.max(modelId.indexOf(':'), 0));
        String env = switch (provider) {
            case "openai" -> "OPENAI_API_KEY";
            case "deepseek" -> "DEEPSEEK_API_KEY";
            case "dashscope" -> "DASHSCOPE_API_KEY";
            case "anthropic" -> "ANTHROPIC_API_KEY";
            case "gemini" -> "GEMINI_API_KEY";
            default -> "该 provider 要求的 API Key";
        };
        boolean openRouter =
                props.getBaseUrl() != null && props.getBaseUrl().toLowerCase().contains("openrouter");
        return "缺少模型凭据。请设置环境变量 " + env
                + (openRouter ? " 或 OPENROUTER_API_KEY" : "")
                + "（或 devmentor.api-key），或改用 --model 指定其它模型。\n"
                + "示例：\n"
                + "  set OPENROUTER_API_KEY=sk-or-...\n"
                + "  java -jar devmentor.jar --model openai:minimax/minimax-m3.1-flash:free\n"
                + "  java -jar devmentor.jar --model ollama:qwen2.5-coder";
    }

    private static String rootMessage(Throwable t) {
        Throwable cur = t;
        while (cur.getCause() != null && cur.getCause() != cur) {
            cur = cur.getCause();
        }
        String msg = cur.getMessage();
        return msg == null || msg.isBlank() ? cur.getClass().getSimpleName() : msg;
    }

    private static String blankToNull(String value) {
        return value == null || value.isBlank() ? null : value.trim();
    }
}
