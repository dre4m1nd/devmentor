# 04 Stream 与 Lambda

## 学习目标

- 用 `map/filter/reduce/collect` 写出可读的数据流水线
- 知道 Stream 是**惰性**的，没有终止操作就什么都不会发生
- 分清 `map` 与 `flatMap`，会用 `Collectors.groupingBy` 做分组统计

## 关键概念

### 惰性与终止操作

```java
var stream = java.util.stream.Stream.of(1, 2, 3)
        .filter(n -> { System.out.println("filter " + n); return n > 1; });
// 到这里什么都没打印 —— 没有终止操作
long count = stream.count();   // 现在才执行
```

### map vs flatMap

```java
var words = java.util.List.of("hello world", "java stream");
var letters = words.stream()
        .flatMap(w -> java.util.Arrays.stream(w.split("")))   // 每个元素展开成多个
        .distinct()
        .toList();
```

### 常用收集器

```java
record Order(String customer, int amount) {}
var orders = java.util.List.of(new Order("a", 10), new Order("a", 20), new Order("b", 5));

var byCustomer = orders.stream()
        .collect(java.util.stream.Collectors.groupingBy(
                Order::customer,
                java.util.stream.Collectors.summingInt(Order::amount)));
// {a=30, b=5}
```

## 常见坑清单

- 忘记终止操作，以为代码没生效
- 在 `forEach` 里做副作用收集（应该用 `collect`）
- 同一个 Stream 被消费两次 → `IllegalStateException`
- 并行流用在有共享可变状态或很小数据量上，反而更慢
- `Collectors.toMap` 遇到重复 key 抛异常，需要给合并函数

## 练习

**练习 1**：给定 `List<String>`，返回长度大于 3 的单词，去重后按长度升序、同长度按字典序排列。
- 验收标准：使用 `Comparator.comparingInt(String::length).thenComparing(...)`；结果不可变。

**练习 2**：用 `Collectors.partitioningBy` 把订单分成"金额 >= 20"和"小于 20"两组，并各自求和。
- 验收标准：返回 `Map<Boolean, Integer>`，两组都求和（空组为 0）。

**练习 3**：把三层嵌套循环改写成 Stream 流水线，并说明可读性是变好还是变差。
- 验收标准：能指出"Stream 不是万能，嵌套超过两层时 for 循环更清晰"。
