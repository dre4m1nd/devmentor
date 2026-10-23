package dre4m1nd.devmentor.agent;

import io.agentscope.core.permission.PermissionBehavior;
import io.agentscope.core.permission.PermissionContextState;
import io.agentscope.core.permission.PermissionMode;
import io.agentscope.core.permission.PermissionRule;
import java.util.List;
import java.util.Locale;

/**
 * 权限档位到 {@link PermissionContextState} 的映射。
 *
 * <ul>
 *   <li>{@code interactive}（默认）：DEFAULT 模式，但对会改动宿主机状态的工具加 ASK 规则，
 *       执行前必须经用户确认。
 *   <li>{@code read-only}：EXPLORE 模式，只允许只读工具。
 *   <li>{@code full}：BYPASS 模式，不再询问（仅在你完全信任时使用）。
 * </ul>
 */
public final class PermissionProfiles {

    /** 需要显式确认的写类工具。 */
    static final List<String> CONFIRM_TOOLS =
            List.of("execute", "write_file", "edit_file", "skill_manage");

    public static final String INTERACTIVE = "interactive";
    public static final String READ_ONLY = "read-only";
    public static final String FULL = "full";

    private PermissionProfiles() {}

    /**
     * @param profile 档位名，大小写与 {@code _}/{@code -} 均可容忍
     * @return 对应的权限上下文
     * @throws IllegalArgumentException 档位名非法
     */
    public static PermissionContextState of(String profile) {
        String normalized = normalize(profile);
        return switch (normalized) {
            case INTERACTIVE -> interactive();
            case READ_ONLY -> PermissionContextState.builder().mode(PermissionMode.EXPLORE).build();
            case FULL -> PermissionContextState.builder().mode(PermissionMode.BYPASS).build();
            default -> throw new IllegalArgumentException(
                    "未知权限档位 \"" + profile + "\"，可选值：interactive、read-only、full");
        };
    }

    /**
     * interactive：只读工具直接放行，写类工具每次询问。
     *
     * <p>这里必须用 {@link PermissionMode#ACCEPT_EDITS} 而不是 {@code DEFAULT}：DEFAULT 模式的
     * 兜底行为是「一切都要确认」，连 {@code read_file} 都会弹窗，实际不可用；
     * ACCEPT_EDITS 的语义恰好是「只读自动允许，其余询问」。
     */
    private static PermissionContextState interactive() {
        PermissionContextState.Builder builder =
                PermissionContextState.builder().mode(PermissionMode.ACCEPT_EDITS);
        for (String tool : CONFIRM_TOOLS) {
            builder.addAskRule(
                    tool,
                    new PermissionRule(
                            tool, null, PermissionBehavior.ASK, "devmentor-default"));
        }
        return builder.build();
    }

    /** 归一化档位名：小写，下划线转连字符，{@code readonly} 视为 {@code read-only}。 */
    public static String normalize(String profile) {
        if (profile == null || profile.isBlank()) {
            return INTERACTIVE;
        }
        String value = profile.trim().toLowerCase(Locale.ROOT).replace('_', '-');
        if ("readonly".equals(value) || "read".equals(value)) {
            return READ_ONLY;
        }
        if ("bypass".equals(value) || "all".equals(value)) {
            return FULL;
        }
        return value;
    }

    /** 供 CLI 展示的中文说明。 */
    public static String describe(String profile) {
        return switch (normalize(profile)) {
            case INTERACTIVE -> "interactive（写操作前询问）";
            case READ_ONLY -> "read-only（只读，禁止修改）";
            case FULL -> "full（不再询问，谨慎使用）";
            default -> profile;
        };
    }
}
