package dre4m1nd.devmentor.cli;

import static org.assertj.core.api.Assertions.assertThat;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.util.List;
import org.jline.reader.Candidate;
import org.jline.reader.LineReader;
import org.jline.reader.LineReaderBuilder;
import org.jline.reader.ParsedLine;
import org.jline.reader.impl.DefaultParser;
import org.jline.terminal.Terminal;
import org.jline.terminal.TerminalBuilder;
import org.junit.jupiter.api.Test;

/**
 * 用真实的 JLine LineReader + 模拟终端验证补全接线。
 *
 * <p>不用假 ParsedLine：这里走完整的 parser → completer 链路，
 * 因此能覆盖「尾随空格导致 wordIndex 不前进」这类只有真实解析才暴露的问题。
 */
class CompleterIntegrationTest {

    private Terminal dumbTerminal() throws Exception {
        return TerminalBuilder.builder()
                .dumb(true)
                .streams(new ByteArrayInputStream(new byte[0]), new ByteArrayOutputStream())
                .build();
    }

    /** 模拟 JLine 在光标处调用 completer 的过程。 */
    private List<String> completeAt(String line, int cursor) throws Exception {
        SlashCommandCompleter completer = new SlashCommandCompleter();
        LineReader reader =
                LineReaderBuilder.builder()
                        .terminal(dumbTerminal())
                        .parser(new DefaultParser())
                        .completer(completer)
                        .build();
        ParsedLine parsed = reader.getParser().parse(line, cursor);
        List<Candidate> out = new java.util.ArrayList<>();
        completer.complete(reader, parsed, out);
        return out.stream().map(Candidate::value).toList();
    }

    @Test
    void completesCommandNameInRealReader() throws Exception {
        assertThat(completeAt("/lo", 3)).containsExactlyInAnyOrder("/login", "/logout");
    }

    @Test
    void completesArgumentAfterTrailingSpace() throws Exception {
        // 关键回归：光标停在空格之后，DefaultParser 仍然只切出一个词。
        assertThat(completeAt("/mode ", 6))
                .containsExactly("interactive", "read-only", "full");
    }

    @Test
    void completesArgumentPrefixInRealReader() throws Exception {
        assertThat(completeAt("/mode re", 8)).containsExactly("read-only");
    }

    @Test
    void ignoresNonCommandInput() throws Exception {
        assertThat(completeAt("hello", 5)).isEmpty();
        assertThat(completeAt("  /arch ", 8)).isEmpty();
    }
}