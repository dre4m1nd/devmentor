package dre4m1nd.devmentor.config;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import io.agentscope.core.model.Model;
import org.junit.jupiter.api.Test;

class ModelConfigTest {

    @Test
    void missingApiKeyGivesActionableMessage() {
        MentorProperties props = new MentorProperties();
        props.setModelId("openai:minimax/minimax-m3.1-flash:free");
        props.setApiKey("");

        ModelConfig config = new ModelConfig(props);
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

        assertThatThrownBy(() -> new ModelConfig(props).mentorModel())
                .isInstanceOf(DevMentorConfigException.class)
                .hasMessageContaining("provider");
    }

    @Test
    void buildsModelWhenKeyPresent() {
        MentorProperties props = new MentorProperties();
        props.setModelId("openai:minimax/minimax-m3.1-flash:free");
        props.setApiKey("test-key");
        props.setBaseUrl("https://openrouter.ai/api/v1");

        Model model = new ModelConfig(props).mentorModel();
        assertThat(model).isNotNull();
        assertThat(model.getModelName()).isNotBlank();
    }
}
