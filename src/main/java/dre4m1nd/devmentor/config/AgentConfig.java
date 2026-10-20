package dre4m1nd.devmentor.config;

import dre4m1nd.devmentor.workspace.WorkspaceBootstrapper;
import java.nio.file.Path;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * 配置层的 Spring 装配。
 *
 * <p>只保留「与运行时无关」的 bean（工作区引导）。Agent 工厂与 Agent 实例都放在
 * {@code agent} 包的 {@link dre4m1nd.devmentor.agent.MentorAgentConfiguration} 里：
 * 那样依赖方向是单向的 {@code agent → config → workspace}，而这里反过来依赖 agent 会形成
 * 包循环，让两个包都无法单独编译和测试。
 */
@Configuration(proxyBeanMethods = false)
public class AgentConfig {

    @Bean
    public WorkspaceBootstrapper workspaceBootstrapper(MentorProperties props) {
        return new WorkspaceBootstrapper(Path.of(props.getWorkspace()).toAbsolutePath().normalize());
    }
}
