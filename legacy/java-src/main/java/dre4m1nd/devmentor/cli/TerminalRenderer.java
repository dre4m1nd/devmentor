package dre4m1nd.devmentor.cli;

import io.agentscope.core.event.AgentEvent;
import io.agentscope.core.event.AgentEventType;
import io.agentscope.core.event.AllToolsDeniedEvent;
import io.agentscope.core.event.ExceedMaxItersEvent;
import io.agentscope.core.event.TextBlockDeltaEvent;
import io.agentscope.core.event.ThinkingBlockDeltaEvent;
import io.agentscope.core.event.ToolCallStartEvent;
import io.agentscope.core.event.ToolResultEndEvent;
import io.agentscope.core.message.ToolResultState;
import java.io.PrintWriter;
import java.util.Map;
import org.jline.utils.AttributedStyle;

/**
 * 把 {@link AgentEvent} 渲染成终端输出。
 *
 * <p>只用 {@link AttributedStyle} 的样式信息，最终由调用方通过 {@link #paint} 转成 ANSI，
 * 因此非 TTY 环境下可以整体关掉颜色而不影响文本内容。
 */
public class TerminalRenderer {

    private static final int MAX_TOOL_SUMMARY = 300;

    private final PrintWriter out;
    private final boolean color;
    private final boolean showThinking;
    private final boolean verbose;

    private boolean textOpen;
    private boolean toolLineOpen;

    public TerminalRenderer(PrintWriter out, boolean color, boolean showThinking, boolean verbose) {
        this.out = out;
        this.color = color;
        this.showThinking = showThinking;
        this.verbose = verbose;
    }

    /** 渲染单个事件。 */
    public void render(AgentEvent event) {
        if (event == null) {
            return;
        }
        AgentEventType type = event.getType();
        if (type == AgentEventType.TEXT_BLOCK_DELTA && event instanceof TextBlockDeltaEvent delta) {
            closeToolLine();
            textOpen = true;
            out.print(delta.getDelta());
            out.flush();
            return;
        }
        if (type == AgentEventType.THINKING_BLOCK_DELTA
                && event instanceof ThinkingBlockDeltaEvent thinking) {
            if (showThinking) {
                closeToolLine();
                out.print(paint(thinking.getDelta(), AttributedStyle.DEFAULT.faint().italic()));
                out.flush();
            }
            return;
        }
        if (type == AgentEventType.TOOL_CALL_START && event instanceof ToolCallStartEvent start) {
            breakText();
            out.println(paint("⏺ " + start.getToolCallName(), AttributedStyle.DEFAULT.foreground(AttributedStyle.CYAN).bold()));
            out.flush();
            toolLineOpen = true;
            return;
        }
        if (type == AgentEventType.TOOL_RESULT_END && event instanceof ToolResultEndEvent end) {
            renderToolResult(end);
            return;
        }
        if (type == AgentEventType.EXCEED_MAX_ITERS && event instanceof ExceedMaxItersEvent iters) {
            breakText();
            out.println(
                    paint(
                            "⚠ 达到最大推理轮数（" + iters.getMaxIters() + "），已停止。可以换个更小的问法，或 /new 开新会话。",
                            AttributedStyle.DEFAULT.foreground(AttributedStyle.YELLOW)));
            out.flush();
            return;
        }
        if (type == AgentEventType.ALL_TOOLS_DENIED && event instanceof AllToolsDeniedEvent) {
            breakText();
            out.println(
                    paint(
                            "⚠ 本轮所有工具调用都被权限拒绝。可以用 /mode 调整权限档位，或换个不需要工具的问法。",
                            AttributedStyle.DEFAULT.foreground(AttributedStyle.YELLOW)));
            out.flush();
        }
    }

    private void renderToolResult(ToolResultEndEvent end) {
        ToolResultState state = end.getState();
        boolean ok = state == null || state == ToolResultState.SUCCESS;
        AttributedStyle style =
                ok
                        ? AttributedStyle.DEFAULT.foreground(AttributedStyle.GREEN)
                        : AttributedStyle.DEFAULT.foreground(AttributedStyle.RED);
        String label = ok ? "  ↳ 完成" : "  ↳ " + (state == null ? "失败" : stateLabel(state));
        out.println(paint(label, style));
        out.flush();
        toolLineOpen = false;
    }

    private static String stateLabel(ToolResultState state) {
        return switch (state) {
            case ERROR -> "失败";
            case DENIED -> "被拒绝";
            case INTERRUPTED -> "被中断";
            case RUNNING -> "运行中";
            case SUCCESS -> "完成";
        };
    }

    /** 一轮结束：补一个换行，重置状态。 */
    public void finishTurn() {
        if (textOpen || toolLineOpen) {
            out.println();
        }
        textOpen = false;
        toolLineOpen = false;
        out.flush();
    }

    /** 打印一条系统提示（不是模型输出）。 */
    public void system(String message) {
        breakText();
        out.println(paint(message, AttributedStyle.DEFAULT.faint()));
        out.flush();
    }

    /** 打印错误。 */
    public void error(String message) {
        breakText();
        out.println(paint("✖ " + message, AttributedStyle.DEFAULT.foreground(AttributedStyle.RED)));
        out.flush();
    }

    /** 打印成功提示。 */
    public void success(String message) {
        breakText();
        out.println(paint("✔ " + message, AttributedStyle.DEFAULT.foreground(AttributedStyle.GREEN)));
        out.flush();
    }

    /** 工具结果的详情行（用于 /verbose 或 HITL 展示）。 */
    public void detail(String label, String body) {
        breakText();
        out.println(paint(label, AttributedStyle.DEFAULT.bold()));
        String shown = verbose ? body : summarize(body);
        out.println(shown == null ? "" : shown);
        out.flush();
    }

    /** 摘要：取首行，必要时截断。 */
    static String summarize(String body) {
        if (body == null) {
            return "";
        }
        String trimmed = body.strip();
        if (trimmed.isEmpty()) {
            return "(空)";
        }
        int newline = trimmed.indexOf('\n');
        String first = newline >= 0 ? trimmed.substring(0, newline) : trimmed;
        if (first.length() > MAX_TOOL_SUMMARY) {
            first = first.substring(0, MAX_TOOL_SUMMARY) + "…";
        }
        return first;
    }

    /** 把文本按样式转成带 ANSI 的字符串；关闭颜色时原样返回。 */
    String paint(String text, AttributedStyle style) {
        if (!color || text == null || text.isEmpty()) {
            return text == null ? "" : text;
        }
        return new org.jline.utils.AttributedString(text, style).toAnsi();
    }

    private void breakText() {
        if (textOpen) {
            out.println();
            textOpen = false;
        }
    }

    private void closeToolLine() {
        toolLineOpen = false;
    }

    public boolean isShowThinking() {
        return showThinking;
    }

    public boolean isVerbose() {
        return verbose;
    }

    /** 供测试/调试：把工具入参压成一行。 */
    public static String formatToolInput(Map<String, Object> input) {
        if (input == null || input.isEmpty()) {
            return "";
        }
        StringBuilder sb = new StringBuilder();
        input.forEach(
                (k, v) -> {
                    if (!sb.isEmpty()) {
                        sb.append(", ");
                    }
                    String value = String.valueOf(v).replace("\n", " ");
                    if (value.length() > 80) {
                        value = value.substring(0, 80) + "…";
                    }
                    sb.append(k).append('=').append(value);
                });
        return sb.toString();
    }
}
