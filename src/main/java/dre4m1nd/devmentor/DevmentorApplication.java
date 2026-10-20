package dre4m1nd.devmentor;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * DevMentor —— 基于 AgentScope Java 的 Java 编程导师终端智能体。
 *
 * <p>应用以纯终端形态运行（不启动 Web 容器）。数据源与 MyBatis 自动配置被排除：本项目不使
 * 用数据库，保留这些 starter 依赖只是为了不破坏既有工程结构。
 */
@SpringBootApplication(
        exclude = {
            org.springframework.boot.jdbc.autoconfigure.DataSourceAutoConfiguration.class,
            com.baomidou.mybatisplus.autoconfigure.MybatisPlusAutoConfiguration.class
        })
public class DevmentorApplication {

    public static void main(String[] args) {
        SpringApplication.run(DevmentorApplication.class, args);
    }
}
