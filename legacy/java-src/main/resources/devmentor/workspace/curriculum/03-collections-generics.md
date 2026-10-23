# 03 集合与泛型

## 学习目标

- 按访问模式选集合：`ArrayList` / `LinkedList` / `HashMap` / `TreeMap` / `LinkedHashMap`
- 分清 `List` 与 `Set` 的语义差异，知道 `HashSet` 依赖 `equals`+`hashCode`
- 看懂泛型的 `? extends` 与 `? super`，知道 PECS 原则

## 关键概念

### 选型

| 需求 | 选择 | 复杂度 |
| --- | --- | --- |
| 按下标随机访问 | `ArrayList` | O(1) 读，尾部 O(1) 写 |
| 频繁头部插入 | `ArrayDeque`（不是 LinkedList） | O(1) 两端 |
| 键值查找 | `HashMap` | O(1) 平均 |
| 需要有序遍历 | `TreeMap` / `LinkedHashMap` | O(log n) / O(1)+顺序 |
| 去重 | `HashSet` | O(1) 平均 |

### 泛型与 PECS

`Producer Extends, Consumer Super`：

```java
// 只读取 —— 用 extends，可以接受 List<Integer>、List<Long>……
static double sum(java.util.List<? extends Number> src) {
    double s = 0;
    for (Number n : src) s += n.doubleValue();
    return s;
}

// 只写入 —— 用 super，可以写进 List<Number>、List<Object>
static void fill(java.util.List<? super Integer> dst, int count) {
    for (int i = 0; i < count; i++) dst.add(i);
}
```

### 类型擦除带来的三个后果

1. 运行时拿不到 `T` 的真实类型：`new T[]` 不行，`list instanceof List<String>` 也不行
2. 不能重载 `foo(List<String>)` 和 `foo(List<Integer>)`（擦除后签名相同）
3. 泛型数组创建受限，需要 `(T[]) new Object[n]` 并抑制警告

## 常见坑清单

- 用 `LinkedList` 当默认 List（大多数场景比 `ArrayList` 慢）
- 遍历时修改集合 → `ConcurrentModificationException`，要用 `Iterator.remove` 或 `removeIf`
- 把可变对象放进 `HashSet` 后修改它，导致再也找不到
- `Arrays.asList` 返回定长列表，`add` 会抛 `UnsupportedOperationException`

## 练习

**练习 1**：统计一段文本里每个单词出现次数，按次数降序输出前 5。
- 验收标准：用 `HashMap` 计数 + `Stream` 排序；相同次数时按单词字典序。

**练习 2**：实现 `static <T> void copy(List<? super T> dst, List<? extends T> src)`。
- 验收标准：能接受 `copy(List<Number>, List<Integer>)`；不能接受反向参数（编译期报错）。

**练习 3**：解释为什么下面代码编译不过，并给出两种修法。

```java
java.util.List<? extends Number> nums = new java.util.ArrayList<Integer>();
nums.add(1);  // ?
```
- 验收标准：能说出"编译器无法确认实际类型，写入可能破坏类型安全"。
