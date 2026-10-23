package dre4m1nd.devmentor.agent;

import static org.assertj.core.api.Assertions.assertThat;

import io.agentscope.core.agent.RuntimeContext;
import org.junit.jupiter.api.Test;

class MentorSessionTest {

    @Test
    void generatesSessionWhenBlank() {
        MentorSession session = new MentorSession(null, null);
        assertThat(session.getUserId()).isEqualTo("learner");
        assertThat(session.getSessionId()).startsWith("mentor-");
    }

    @Test
    void keepsProvidedIdentity() {
        MentorSession session = new MentorSession("alice", "s-1");
        RuntimeContext ctx = session.runtimeContext();
        assertThat(ctx.getUserId()).isEqualTo("alice");
        assertThat(ctx.getSessionId()).isEqualTo("s-1");
    }

    @Test
    void startNewChangesSessionId() {
        MentorSession session = new MentorSession("alice", "s-1");
        String fresh = session.startNew("My Topic!");
        assertThat(fresh).isNotEqualTo("s-1");
        assertThat(fresh).startsWith("my-topic");
        assertThat(session.getSessionId()).isEqualTo(fresh);
        assertThat(session.getUserId()).isEqualTo("alice");
    }
}
