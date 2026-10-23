# 01 语法与类型系统

## 学习目标

- 分清**基本类型**与**引用类型**，知道自动装箱发生在哪里
- 会用 `var` 做局部变量类型推断，也知道它不能用在字段和参数上
- 理解整数溢出、浮点精度、字符串不可变这三个高频坑

## 关键概念

### 基本类型与包装类型

Java 有 8 种基本类型：`byte short int long float double char boolean`。它们的包装类型（`Integer` 等）是对象，可以放进集合，但代价是装箱拆箱。

```java
Integer a = 127, b = 127;
System.out.println(a == b);      // true —— Integer 缓存 -128..127
Integer c = 128, d = 128;
System.out.println(c == d);      // false —— 超出缓存，是两个对象
System.out.println(c.equals(d)); // true —— 值相等要用 equals
```

### var

`var` 只是**编译期推断**，不是动态类型。它只能用于局部变量，且必须同时初始化。

```java
var list = new java.util.ArrayList<String>();  // 推断为 ArrayList<String>
var n = 1;                                      // int
// var x;            // 编译错误：没有初始化
// var[] arr = ...;  // 编译错误：不能用于数组声明
```

### 三个高频坑

1. **整数溢出静默发生**：`Integer.MAX_VALUE + 1` 变成负数，不报错。涉及金额/计数用 `long` 或 `Math.addExact`。
2. **浮点不精确**：`0.1 + 0.2 != 0.3`。金额用 `BigDecimal`，且要用字符串构造。
3. **字符串不可变**：`String` 的每次"修改"都产生新对象；循环里拼接用 `StringBuilder`。

## 常见坑清单

- 用 `==` 比较字符串/包装类型
- `switch` 忘写 `break`（传统写法）
- `char` 与 `int` 隐式互转导致 `'A' + 1` 得到 66 而不是 "B"
- 三元运算符两侧类型不一致触发意外的自动拆箱

## 练习

**练习 1（基础）**：写一个方法，接收 `int` 秒数，返回 `"1h 2m 3s"` 格式。
- 验收标准：输入 0 返回 `"0s"`；输入负数抛 `IllegalArgumentException`；输入 3661 返回 `"1h 1m 1s"`。

**练习 2（易错）**：解释并修复下面这段代码的 bug：

```java
Integer total = 0;
for (int i = 0; i < 1000; i++) {
    total += i;   // 编译通过，但……
}
```
- 验收标准：能指出这是拆箱/装箱导致的性能与空指针风险，并给出 `int` 或 `long` 的改法。

**练习 3（进阶）**：用 `BigDecimal` 实现 `addPrice`，要求输入 `"19.99"` 与 `"0.01"` 精确得到 `20.00`。
- 验收标准：不能出现 `19.999999999999996`；构造 `BigDecimal` 时用字符串而非 double。
