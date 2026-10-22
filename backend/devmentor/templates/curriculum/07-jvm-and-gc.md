# 07 JVM 与内存

## 学习目标

- 说清堆、栈、元空间各放什么，`OutOfMemoryError` 有哪几种
- 理解分代回收与常见 GC（G1、ZGC）的取舍
- 会用 `jcmd` / `jstack` 做初步诊断

## 关键概念

### 内存区域

| 区域 | 存放 | 线程共享 | 典型错误 |
| --- | --- | --- | --- |
| 堆 | 对象实例 | 是 | `OutOfMemoryError: Java heap space` |
| 虚拟机栈 | 栈帧、局部变量 | 否 | `StackOverflowError` |
| 元空间 | 类元数据 | 是 | `OutOfMemoryError: Metaspace` |
| 方法区常量池 | 字符串常量等 | 是 | 大量 `intern` 导致膨胀 |

### 分代与 GC

- 新对象进 Eden，Minor GC 后存活对象进 Survivor，多次存活后晋升老年代
- **G1**：默认选择，按 Region 回收，可设停顿目标 `-XX:MaxGCPauseMillis`
- **ZGC**：超低停顿（亚毫秒级），适合大堆，代价是吞吐略低

### 常用诊断命令

```bash
jcmd <pid> GC.heap_info          # 堆使用概况
jcmd <pid> Thread.print          # 线程栈
jcmd <pid> VM.flags              # 启动参数
jmap -histo:live <pid> | head    # 存活对象直方图
```

## 常见坑清单

- 把 `-Xmx` 设得远大于物理内存，导致 swap 抖动
- 用 `System.gc()` 试图"手动回收"
- 长生命周期集合持有短生命周期对象（内存泄漏的典型形态）
- 大量字符串拼接产生中间对象，用 `StringBuilder`
- 在循环里创建线程池或 `Connection`

## 练习

**练习 1**：写一段会触发 `OutOfMemoryError: Java heap space` 的代码，并用 `-Xmx64m` 验证。
- 验收标准：能解释为什么 `List<byte[]>` 持续增长会 OOM，而局部变量不会。

**练习 2**：写一段触发 `StackOverflowError` 的递归，并说明和 OOM 的区别。
- 验收标准：能指出两者发生在不同内存区域。

**练习 3**：给定 `jcmd GC.heap_info` 输出，判断当前是否频繁 Full GC。
- 验收标准：能看懂 Eden/Old 的占用比例，并说出该调 `-Xmx` 还是查泄漏。
