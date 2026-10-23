package dre4m1nd.devmentor;

import static org.assertj.core.api.Assertions.assertThat;

import dre4m1nd.devmentor.agent.MentorAgentFactory;
import dre4m1nd.devmentor.config.MentorProperties;
import io.agentscope.harness.agent.HarnessAgent;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

/**
 * 上下文装配冒烟测试。
 *
 * <p>关闭 CLI（否则会占用 stdin）、把工作区与状态目录指向 target/，并用假 Key 让模型 bean 可以
 * 构造（不会发起网络请求）。
 */
@SpringBootTest(
        properties = {
            "devmentor.cli.enabled=false",
            "devmentor.api-key=test-key",
            "devmentor.workspace=target/test-workspace",
            "devmentor.state-dir=target/test-state"
        })
class DevmentorApplicationTests {

    @Autowired private MentorProperties props;

    @Autowired private HarnessAgent mentorAgent;

    @Autowired private MentorAgentFactory factory;

    @Test
    void contextLoads() {
        assertThat(props).isNotNull();
        assertThat(factory).isNotNull();
        assertThat(mentorAgent).isNotNull();
    }

    @Test
    void agentExposesMentorTools() {
        assertThat(mentorAgent.getToolkit().getToolNames())
                .contains("java_compile_check", "java_run_snippet", "curriculum_list", "progress_read");
    }

    @Test
    void workspaceIsBootstrapped() {
        assertThat(factory.workspaceDir().resolve("AGENTS.md")).exists();
        assertThat(factory.workspaceDir().resolve("curriculum")).isDirectory();
    }
}
