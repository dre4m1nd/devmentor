# 08 测试与 Spring 入门

## 学习目标

- 用 JUnit 5 + AssertJ 写出可读的测试，覆盖边界而不是只覆盖正常路径
- 分清单元测试与集成测试，知道什么时候该用 `@SpringBootTest`
- 理解依赖注入的三种方式，以及为什么推荐构造器注入

## 关键概念

### 一个合格的测试

```java
import static org.assertj.core.api.Assertions.*;

class AgeParserTest {

    @Test
    void 空值返回空() {
        assertThat(AgeParser.parse(null)).isEmpty();
    }

    @Test
    void 非法输入抛异常且带原始值() {
        assertThatThrownBy(() -> AgeParser.parse("abc"))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("abc");
    }

    @Test
    void 边界值() {
        assertThat(AgeParser.parse("0")).hasValue(0);
        assertThat(AgeParser.parse("150")).hasValue(150);
        assertThatThrownBy(() -> AgeParser.parse("151"))
                .isInstanceOf(IllegalArgumentException.class);
    }
}
```

### 单元测试 vs 集成测试

- 单元测试：不启动容器，毫秒级，覆盖逻辑分支
- `@SpringBootTest`：启动上下文，验证装配是否正确（例如"排除数据源自动配置后能否启动"）
- 能用单元测试证明的，不要用集成测试

### 构造器注入

```java
@Service
public class OrderService {
    private final OrderRepository repo;
    public OrderService(OrderRepository repo) { this.repo = repo; }   // 依赖不可变、可测试
}
```

字段注入（`@Autowired` 打在字段上）隐藏依赖、无法 `final`、单测要反射，不推荐。

## 常见坑清单

- 只测 happy path，边界（0、负数、空、超长）没测
- 测试之间共享可变状态，顺序一变就挂
- 用 `Thread.sleep` 等待异步结果
- 断言只写 `assertTrue(x != null)`，失败时看不出实际值
- 集成测试里连真实数据库/网络，导致 CI 不稳定

## 练习

**练习 1**：为 `StringUtils.isBlank` 写 6 个测试用例，覆盖 null、空串、空格、正常串、全角空格、制表符。
- 验收标准：每个用例名能说明它验证什么；失败时输出可读。

**练习 2**：给一个依赖外部 HTTP 的服务写单元测试，用假实现替换 HTTP 调用。
- 验收标准：测试不发起真实网络请求；能模拟超时和 500 两种失败。

**练习 3**：解释为什么 `@SpringBootTest` 在没有数据源配置时会失败，并给出两种修法。
- 验收标准：能说出"排除自动配置"和"提供测试用内存数据源"两条路径。
