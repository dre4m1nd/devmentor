package dre4m1nd.devmentor.cli;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.ArrayList;
import java.util.List;
import org.jline.reader.Candidate;
import org.jline.reader.ParsedLine;
import org.jline.reader.impl.DefaultParser;
import org.junit.jupiter.api.Test;

class SlashCommandCompleterTest {

    private final SlashCommandCompleter completer = new SlashCommandCompleter();

    /** 用真实 parser 解析整行，模拟 JLine 传给 Completer 的 ParsedLine。 */
    private List<Candidate> complete(String line) {
        ParsedLine parsed = new DefaultParser().parse(line, line.length());
        List<Candidate> out = new ArrayList<>();
        completer.complete(null, parsed, out);
        return out;
    }

    @Test
    void emptySlashListsAllCommands() {
        List<String> names = complete("/").stream().map(Candidate::value).toList();

        assertThat(names).contains("/login", "/logout", "/model", "/arch", "/help");
        // /exit 与 /quit 重复，菜单里不应出现
        assertThat(names).doesNotContain("/exit");
    }

    @Test
    void prefixFiltersCommands() {
        List<String> names = complete("/lo").stream().map(Candidate::value).toList();

        assertThat(names).containsExactlyInAnyOrder("/login", "/logout");
    }

    @Test
    void candidatesCarryDescriptions() {
        List<Candidate> candidates = complete("/logi");

        assertThat(candidates).hasSize(1);
        assertThat(candidates.get(0).descr()).isNotBlank();
    }

    @Test
    void plainTextGetsNoCandidates() {
        assertThat(complete("你好")).isEmpty();
        assertThat(complete("explain streams")).isEmpty();
    }

    @Test
    void modeArgumentCompletesFixedValues() {
        List<String> values = complete("/mode ").stream().map(Candidate::value).toList();

        assertThat(values).containsExactly("interactive", "read-only", "full");
    }

    @Test
    void modeArgumentFiltersByPrefix() {
        List<String> values = complete("/mode re").stream().map(Candidate::value).toList();

        assertThat(values).containsExactly("read-only");
    }

    @Test
    void langArgumentCompletesZhEn() {
        assertThat(complete("/lang ").stream().map(Candidate::value).toList())
                .containsExactly("zh", "en");
    }

    @Test
    void commandWithoutFixedArgumentsOffersNothing() {
        // /arch 接受任意路径，不该硬塞候选
        assertThat(complete("/arch ")).isEmpty();
    }

    @Test
    void argumentCandidatesCarryDescriptions() {
        List<Candidate> candidates = complete("/mode i");

        assertThat(candidates).hasSize(1);
        assertThat(candidates.get(0).descr()).contains("询问");
    }
}
