package dre4m1nd.devmentor.cli;

import static org.assertj.core.api.Assertions.assertThat;

import io.agentscope.core.event.TextBlockDeltaEvent;
import io.agentscope.core.event.ToolCallStartEvent;
import io.agentscope.core.event.ToolResultEndEvent;
import io.agentscope.core.message.ToolResultState;
import java.io.PrintWriter;
import java.io.StringWriter;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class TerminalRendererTest {

    private final StringWriter sink = new StringWriter();
    private final PrintWriter out = new PrintWriter(sink, true);

    @Test
    void concatenatesTextDeltas() {
        TerminalRenderer renderer = new TerminalRenderer(out, false, false, false);
        renderer.render(new TextBlockDeltaEvent("r1", "b1", "你好"));
        renderer.render(new TextBlockDeltaEvent("r1", "b1", "，世界"));
        renderer.finishTurn();
        assertThat(sink.toString()).contains("你好，世界");
    }

    @Test
    void noAnsiWhenColorDisabled() {
        TerminalRenderer renderer = new TerminalRenderer(out, false, false, false);
        renderer.render(new ToolCallStartEvent("r1", "c1", "java_run_snippet"));
        assertThat(sink.toString()).doesNotContain("\u001B[");
        assertThat(sink.toString()).contains("java_run_snippet");
    }

    @Test
    void colorsWhenEnabled() {
        TerminalRenderer renderer = new TerminalRenderer(out, true, false, false);
        renderer.render(new ToolCallStartEvent("r1", "c1", "read_file"));
        assertThat(sink.toString()).contains("\u001B[");
    }

    @Test
    void marksFailedToolResult() {
        TerminalRenderer renderer = new TerminalRenderer(out, false, false, false);
        renderer.render(new ToolResultEndEvent("r1", "c1", "read_file", ToolResultState.ERROR));
        assertThat(sink.toString()).contains("失败");
    }

    @Test
    void summarizeKeepsFirstLineAndTruncates() {
        assertThat(TerminalRenderer.summarize("第一行\n第二行")).isEqualTo("第一行");
        assertThat(TerminalRenderer.summarize("x".repeat(400))).hasSizeLessThan(400);
        assertThat(TerminalRenderer.summarize("   ")).isEqualTo("(空)");
    }

    @Test
    void formatsToolInput() {
        String formatted = TerminalRenderer.formatToolInput(Map.of("source", "class A {}"));
        assertThat(formatted).contains("source=");
    }

    @Test
    void friendlyMessagesCoverCommonHttpErrors() {
        assertThat(DevMentorCli.friendly("HTTP 429 Too Many Requests")).contains("限流");
        assertThat(DevMentorCli.friendly("401 Unauthorized")).contains("鉴权");
        assertThat(DevMentorCli.friendly("403 Forbidden")).contains("拒绝");
        assertThat(DevMentorCli.friendly("connection timeout")).contains("超时");
        assertThat(DevMentorCli.friendly("something else")).isEqualTo("something else");
    }
}
