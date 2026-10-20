package dre4m1nd.devmentor.agent;

import dre4m1nd.devmentor.config.MentorProperties;
import dre4m1nd.devmentor.workspace.WorkspaceBootstrapper;
import io.agentscope.core.model.Model;
import io.agentscope.harness.agent.HarnessAgent;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * Agent 运行时层的 Spring 装配：工厂与进程内共享的 Agent 实例都放在这里。
 *
 * <p>这两个 bean 原先在 {@code config.AgentConfig} 里，而 {@link MentorAgentFactory} 又依赖
 * {@code config.MentorProperties}，于是形成 {@code agent → config → agent} 的包循环：
 * 两个包都无法单独编译、单独测试。搬到运行时所在的 {@code agent} 包后，依赖变成单向的
 * {@code agent → config → workspace}，方向与运行时到装配层的语义一致。
 *
 * <p>消费方不需要改动：Spring 组件扫描覆盖整个 {@code dre4m1nd.devmentor} 包。
 */
@Configuration(proxyBeanMethods = false)
public class MentorAgentConfiguration {

    /**
     * 工厂持有一个 {@link ObjectProvider} 而非 {@link Model} 本身：模型要到真正建 Agent 时
     * 才解析，因此没有 API Key 时上下文依然能启动，{@code --self-check} 可以先做装配检查。
     */
    @Bean
    public MentorAgentFactory mentorAgentFactory(
            MentorProperties props,
            ObjectProvider<Model> modelProvider,
            WorkspaceBootstrapper bootstrapper) {
        return new MentorAgentFactory(props, modelProvider::getObject, bootstrapper);
    }

    /**
     * 进程内共享的导师 Agent。REPL 是单线程的，关停时由 Spring 调用 {@code close()}。
     *
     * <p>延迟创建：没有 API Key 时上下文仍可启动，{@code --self-check} 因此能先跑装配检查，
     * 再由 CLI 决定是打印指引还是进入对话。
     */
    @Bean(destroyMethod = "close")
    @org.springframework.context.annotation.Lazy
    public HarnessAgent mentorAgent(MentorAgentFactory factory) {
        return factory.create();
    }
}
