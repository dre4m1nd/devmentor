package dre4m1nd.devmentor.cli;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

class DevMentorCliTest {

    @Test
    void countsCjkAsDoubleWidth() {
        assertThat(DevMentorCli.displayWidth("abc")).isEqualTo(3);
        assertThat(DevMentorCli.displayWidth("编程")).isEqualTo(4);
        assertThat(DevMentorCli.displayWidth("a编b")).isEqualTo(4);
        assertThat(DevMentorCli.displayWidth("")).isZero();
    }

    @Test
    void friendlyMapsHttpErrorsToActionableAdvice() {
        assertThat(DevMentorCli.friendly("401 Unauthorized")).contains("鉴权").contains("OPENROUTER_API_KEY");
        assertThat(DevMentorCli.friendly("429 Too Many Requests")).contains("限流").contains("/model");
        assertThat(DevMentorCli.friendly("402 Payment Required")).contains("额度");
        assertThat(DevMentorCli.friendly("403 Forbidden")).contains("拒绝");
        assertThat(DevMentorCli.friendly("read timed out")).contains("超时");
        assertThat(DevMentorCli.friendly("boom")).isEqualTo("boom");
        assertThat(DevMentorCli.friendly(null)).isEqualTo("未知错误。");
    }
}
