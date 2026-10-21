package dre4m1nd.devmentor.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * 凭据存储的装配。
 *
 * <p>单独成类而不是放进 {@link ModelConfig}：{@code ModelConfig} 自己也注入
 * {@link CredentialStore}，把 bean 定义和注入放在同一个类里会形成构造期循环依赖，
 * Spring 启动时直接失败。
 */
@Configuration(proxyBeanMethods = false)
public class CredentialConfig {

    /** {@code /login} 与模型装配共享同一个实例，因此登录后立刻生效，不必重启。 */
    @Bean
    public CredentialStore credentialStore() {
        return CredentialStore.defaultStore();
    }
}
