package dre4m1nd.devmentor.agent;

import io.agentscope.core.agent.RuntimeContext;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Locale;
import java.util.UUID;

/**
 * 当前会话身份。会话 id 决定 AgentState 的寻址，因此 {@code /new} 只需要换一个 id。
 */
public class MentorSession {

    private static final DateTimeFormatter STAMP = DateTimeFormatter.ofPattern("yyyyMMdd-HHmmss");

    private final String userId;
    private String sessionId;

    public MentorSession(String userId, String sessionId) {
        this.userId = (userId == null || userId.isBlank()) ? "learner" : userId.trim();
        this.sessionId =
                (sessionId == null || sessionId.isBlank()) ? newSessionId("mentor") : sessionId.trim();
    }

    /** 生成形如 {@code mentor-20261020-101530} 的会话 id。 */
    public static String newSessionId(String prefix) {
        return prefix + "-" + LocalDateTime.now().format(STAMP);
    }

    /** 开启一个新会话，返回新的会话 id。 */
    public String startNew(String name) {
        String prefix = (name == null || name.isBlank()) ? "mentor" : sanitize(name);
        this.sessionId = newSessionId(prefix) + "-" + UUID.randomUUID().toString().substring(0, 4);
        return this.sessionId;
    }

    public RuntimeContext runtimeContext() {
        return RuntimeContext.builder().userId(userId).sessionId(sessionId).build();
    }

    public String getUserId() {
        return userId;
    }

    public String getSessionId() {
        return sessionId;
    }

    private static String sanitize(String raw) {
        String cleaned = raw.trim().toLowerCase(Locale.ROOT).replaceAll("[^a-z0-9._-]", "-");
        return cleaned.isEmpty() ? "mentor" : cleaned;
    }
}
