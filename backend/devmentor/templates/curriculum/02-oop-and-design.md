# 02 面向对象与设计

## 学习目标

- 分清**继承**与**组合**，知道什么时候该用哪个
- 会用 `record`、`sealed`、`interface` 默认方法表达类型关系
- 理解封装真正的含义：不是"给字段加 getter"，而是"不变量由谁守护"

## 关键概念

### record 不是"简化版 POJO"

`record` 的语义是**不可变的值**：组件 final、自动生成 `equals/hashCode/toString`、适合做 DTO、Map 的 key、模式匹配的载体。

```java
public record Money(java.math.BigDecimal amount, String currency) {
    public Money {                       // 紧凑构造器：校验不变量
        if (amount.signum() < 0) throw new IllegalArgumentException("金额不能为负");
        java.util.Objects.requireNonNull(currency);
    }
    public Money plus(Money other) {     // 值对象上的行为也很自然
        if (!currency.equals(other.currency)) throw new IllegalArgumentException("币种不同");
        return new Money(amount.add(other.amount), currency);
    }
}
```

### sealed 表达封闭的类型集合

```java
public sealed interface Shape permits Circle, Square {}
public record Circle(double r) implements Shape {}
public record Square(double side) implements Shape {}

double area(Shape s) {
    return switch (s) {                   // 编译器知道只有两种，无需 default
        case Circle c -> Math.PI * c.r() * c.r();
        case Square q -> q.side() * q.side();
    };
}
```

### 继承 vs 组合

- 继承表达 "is-a"，且**父类的实现细节会泄漏给子类**（脆弱基类问题）
- 组合表达 "has-a"，更容易替换与测试
- 默认选组合；只有在确实需要多态替换且父类为它设计过（有文档承诺）时才继承

## 常见坑清单

- 为了复用代码而继承（应该用组合或工具方法）
- 在构造器里调用可被重写的方法
- `equals` 重写但 `hashCode` 没重写，导致 `HashMap` 找不到 key
- `record` 里塞可变字段（`List` 组件没有防御性拷贝）

## 练习

**练习 1**：把 `class Point { int x, y; }` 改写成 `record`，并补一个 `distanceTo` 方法。
- 验收标准：`new Point(0,0).equals(new Point(0,0))` 为 true；`distanceTo` 用 `Math.hypot`。

**练习 2**：用 `sealed interface` + `record` 建模"成功/失败"两种结果，并写一个 `map` 方法只在成功时变换值。
- 验收标准：`switch` 不写 `default` 也能编译通过；失败分支原样传递错误信息。

**练习 3（设计题）**：有个 `EmailSender extends Sender` 只为复用 `send` 方法。改成组合后，代码结构变成什么样？各有什么代价？
- 验收标准：能说出"继承把父类所有公开方法都暴露出去"这一具体代价。
