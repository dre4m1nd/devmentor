# 06 并发基础

## 学习目标

- 说清**原子性、可见性、有序性**三个问题分别由什么机制解决
- 会用 `synchronized`、`ReentrantLock`、`AtomicInteger`、`ConcurrentHashMap`
- 知道 `volatile` 能做什么、不能做什么

## 关键概念

### 三个问题与对应手段

| 问题 | 表现 | 手段 |
| --- | --- | --- |
| 原子性 | `count++` 丢更新 | `synchronized`、`AtomicInteger`、`LongAdder` |
| 可见性 | 一个线程改了，另一个看不到 | `volatile`、锁、`Atomic` 类 |
| 有序性 | 指令重排导致半初始化对象 | `volatile`、`final`、happens-before |

### volatile 的边界

```java
private volatile boolean running = true;   // 适合：状态标志
private volatile int counter = 0;
counter++;   // 不安全！读-改-写三步，volatile 不保证原子性
```

### 线程池不要用 Executors 快捷方法

```java
// 风险：无界队列可能 OOM
var bad = java.util.concurrent.Executors.newFixedThreadPool(4);
// 推荐：显式参数 + 有界队列 + 拒绝策略
var pool = new java.util.concurrent.ThreadPoolExecutor(
        4, 8, 60, java.util.concurrent.TimeUnit.SECONDS,
        new java.util.concurrent.ArrayBlockingQueue<>(100),
        new java.util.concurrent.ThreadPoolExecutor.CallerRunsPolicy());
```

### 虚拟线程（Java 21+）

IO 密集场景可用 `Executors.newVirtualThreadPerTaskExecutor()`，但**不要**用它包裹 CPU 密集任务，也不要在里面用 `synchronized` 长时间持锁（会 pin 住载体线程）。

## 常见坑清单

- 用 `volatile` 保护复合操作
- 在 `synchronized` 块里做 IO / 调用外部服务
- 双重检查锁忘记 `volatile`
- 用 `ConcurrentHashMap` 的 `size()` 做精确判断（它是近似值）
- 忘记关闭线程池，导致进程不退出

## 练习

**练习 1**：写一个线程安全的计数器，分别用 `synchronized` 和 `AtomicInteger` 实现，压测 10 万次累加。
- 验收标准：两种实现结果都是 100000；能说出各自的适用场景。

**练习 2**：解释下面代码为什么可能死循环，并修复。

```java
class Worker {
    private boolean stopped = false;
    void stop() { stopped = true; }
    void run() { while (!stopped) { /* ... */ } }
}
```
- 验收标准：能说出"可见性问题"，并把字段改成 `volatile`（或说明用锁的方案）。

**练习 3**：用 `CompletableFuture` 并行调用两个模拟服务，任一失败时返回降级值。
- 验收标准：使用 `exceptionally` 或 `handle`；总耗时接近较慢的那个而不是两者之和。
