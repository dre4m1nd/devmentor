package dre4m1nd.devmentor.config;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import io.agentscope.core.model.Model;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import org.junit.jupiter.api.Test;

class ModelConfigTest {

    /** 指向一个不存在的凭据文件：测试不读开发机上真实的 ~/.devmentor/credentials。 */
    private static CredentialStore emptyStore() {
        try {
            Path dir = Files.createTempDirectory("devmentor-cred");
            return new CredentialStore(dir.resolve("credentials"));
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    @Test
    void missingApiKeyGivesActionableMessage() {
        MentorProperties props = new MentorProperties();
        props.setModelId("openai:minimax/minimax-m3.1-flash:free");
        props.setApiKey("");

        ModelConfig config = new ModelConfig(props, emptyStore());
        assertThatThrownBy(config::mentorModel)
                .isInstanceOf(DevMentorConfigException.class)
                .hasMessageContaining("OPENAI_API_KEY")
                .hasMessageContaining("--model");
    }

    @Test
    void rejectsModelIdWithoutProviderPrefix() {
        MentorProperties props = new MentorProperties();
        props.setModelId("just-a-model");
        props.setApiKey("k");

        assertThatThrownBy(() -> new ModelConfig(props, emptyStore()).mentorModel())
                .isInstanceOf(DevMentorConfigException.class)
                .hasMessageContaining("provider");
    }

    @Test
    void buildsModelWhenKeyPresent() {
        MentorProperties props = new MentorProperties();
        props.setModelId("openai:minimax/minimax-m3.1-flash:free");
        props.setApiKey("test-key");
        props.setBaseUrl("https://openrouter.ai/api/v1");

        Model model = new ModelConfig(props, emptyStore()).mentorModel();
        assertThat(model).isNotNull();
        assertThat(model.getModelName()).isNotBlank();
    }
}