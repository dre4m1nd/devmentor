package dre4m1nd.devmentor.cli;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

class SlashCommandsTest {

    @Test
    void detectsCommands() {
        assertThat(SlashCommands.isCommand("/help")).isTrue();
        assertThat(SlashCommands.isCommand("你好")).isFalse();
        assertThat(SlashCommands.isCommand(null)).isFalse();
    }

    @Test
    void parsesNameAndArgs() {
        SlashCommands.Parsed parsed = SlashCommands.parse("/mode read-only");
        assertThat(parsed).isNotNull();
        assertThat(parsed.name()).isEqualTo("mode");
        assertThat(parsed.arg(0)).isEqualTo("read-only");
        assertThat(parsed.arg(1)).isNull();
    }

    @Test
    void normalizesCaseAndExtraSpaces() {
        SlashCommands.Parsed parsed = SlashCommands.parse("  /LANG   en  ");
        assertThat(parsed).isNotNull();
        assertThat(parsed.name()).isEqualTo("lang");
        assertThat(parsed.arg(0)).isEqualTo("en");
    }

    @Test
    void rejectsBareSlash() {
        assertThat(SlashCommands.parse("/")).isNull();
    }

    @Test
    void knowsDocumentedCommands() {
        assertThat(SlashCommands.isKnown("help")).isTrue();
        assertThat(SlashCommands.isKnown("nope")).isFalse();
        assertThat(SlashCommands.helpText()).contains("/mode").contains("/lesson");
        assertThat(SlashCommands.commandNames()).contains("/help", "/quit");
    }
}
