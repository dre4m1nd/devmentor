package dre4m1nd.devmentor.config;

import static org.assertj.core.api.Assertions.assertThat;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class CredentialStoreTest {

    @TempDir Path dir;

    private CredentialStore store() {
        return new CredentialStore(dir.resolve("credentials"));
    }

    @Test
    void loadReturnsEmptyWhenFileMissing() {
        assertThat(store().load()).isEmpty();
        assertThat(store().find("openai")).isNull();
    }

    @Test
    void saveThenLoadRoundTrips() throws Exception {
        CredentialStore s = store();
        s.save("deepseek", "sk-deepseek-123");

        assertThat(s.find("deepseek")).isEqualTo("sk-deepseek-123");
        assertThat(s.load()).containsEntry("deepseek", "sk-deepseek-123");
    }

    @Test
    void saveOverwritesSameProvider() throws Exception {
        CredentialStore s = store();
        s.save("openai", "old-key");
        s.save("openai", "new-key");

        assertThat(s.load()).containsExactly(Map.entry("openai", "new-key"));
    }

    @Test
    void providerLookupIsCaseInsensitive() throws Exception {
        CredentialStore s = store();
        s.save("OpenAI", "k1");

        assertThat(s.find("openai")).isEqualTo("k1");
        assertThat(s.find("OPENAI")).isEqualTo("k1");
    }

    @Test
    void removeDeletesOnlyTargetProvider() throws Exception {
        CredentialStore s = store();
        s.save("openai", "k1");
        s.save("deepseek", "k2");

        s.remove("openai");

        assertThat(s.find("openai")).isNull();
        assertThat(s.find("deepseek")).isEqualTo("k2");
    }

    @Test
    void ignoresCommentsAndMalformedLines() throws Exception {
        Path file = dir.resolve("credentials");
        Files.writeString(
                file,
                "# a comment\n"
                        + "\n"
                        + "no-equals-sign\n"
                        + "openai=sk-abc\n"
                        + "  deepseek = sk-def  \n");

        CredentialStore s = new CredentialStore(file);
        assertThat(s.load())
                .containsExactly(MapEntry.of("openai", "sk-abc"), MapEntry.of("deepseek", "sk-def"));
    }

    /** Map.entry 不允许 null，这里只是让断言更紧凑的小工具。 */
    private static final class MapEntry {
        static Map.Entry<String, String> of(String k, String v) {
            return new java.util.AbstractMap.SimpleEntry<>(k, v);
        }
    }
}
