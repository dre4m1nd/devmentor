package dre4m1nd.devmentor.cli;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;

class CliOptionsTest {

    @Test
    void parsesFlags() {
        CliOptions options =
                CliOptions.parse(
                        new String[] {"--model", "openai:x", "--session", "s2", "--mode", "full",
                                "--no-color", "--verbose", "--think"});
        assertThat(options.getModel()).isEqualTo("openai:x");
        assertThat(options.getSession()).isEqualTo("s2");
        assertThat(options.getMode()).isEqualTo("full");
        assertThat(options.isNoColor()).isTrue();
        assertThat(options.isVerbose()).isTrue();
        assertThat(options.isThink()).isTrue();
    }

    @Test
    void parsesAskAndSelfCheck() {
        assertThat(CliOptions.parse(new String[] {"--ask", "你好"}).getAsk()).isEqualTo("你好");
        assertThat(CliOptions.parse(new String[] {"--self-check"}).isSelfCheck()).isTrue();
    }

    @Test
    void treatsBareArgumentAsAsk() {
        assertThat(CliOptions.parse(new String[] {"解释一下泛型"}).getAsk()).isEqualTo("解释一下泛型");
    }

    @Test
    void requiresValueForFlag() {
        assertThatThrownBy(() -> CliOptions.parse(new String[] {"--model"}))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("--model");
    }
}
