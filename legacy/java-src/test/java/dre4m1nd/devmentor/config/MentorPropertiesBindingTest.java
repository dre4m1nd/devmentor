package dre4m1nd.devmentor.config;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;
import org.springframework.boot.context.properties.bind.Binder;
import org.springframework.boot.context.properties.source.MapConfigurationPropertySource;

class MentorPropertiesBindingTest {

    @Test
    void defaultsAreUsable() {
        MentorProperties props = new MentorProperties();
        assertThat(props.getModelId()).contains(":");
        assertThat(props.getLanguage()).isEqualTo("zh");
        assertThat(props.getPermissionMode()).isEqualTo("interactive");
        assertThat(props.getMaxIters()).isGreaterThan(0);
        assertThat(props.getTools().getJavaRun().isEnabled()).isTrue();
        assertThat(props.getTools().getJavaRun().getTimeoutSeconds()).isPositive();
        assertThat(props.getCli().isEnabled()).isTrue();
        assertThat(props.isEnableShell()).isFalse();
    }

    @Test
    void bindsNestedKeys() {
        var source =
                new MapConfigurationPropertySource(
                        java.util.Map.of(
                                "devmentor.model-id", "openai:some/model:free",
                                "devmentor.tools.java-run.timeout-seconds", "3",
                                "devmentor.cli.enabled", "false",
                                "devmentor.enable-shell", "true"));
        MentorProperties props =
                new Binder(source).bind("devmentor", MentorProperties.class).get();
        assertThat(props.getModelId()).isEqualTo("openai:some/model:free");
        assertThat(props.getTools().getJavaRun().getTimeoutSeconds()).isEqualTo(3);
        assertThat(props.getCli().isEnabled()).isFalse();
        assertThat(props.isEnableShell()).isTrue();
    }
}
