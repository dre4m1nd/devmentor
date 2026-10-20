# 05 异常与 IO

## 学习目标

- 分清受检异常与运行时异常，知道该在哪一层处理
- 会用 try-with-resources，理解它等价于什么
- 读写文件时显式指定字符集，避免平台默认编码

## 关键概念

### 异常分类与处理原则

- **受检异常**（`IOException`）：调用方必须处理，表达"可预期的外部失败"
- **运行时异常**（`IllegalArgumentException`、`NullPointerException`）：编程错误，应修代码而不是吞掉
- 原则：**能处理的才 catch，处理不了就往上抛**；不要 `catch (Exception e) {}`

### try-with-resources

```java
try (var reader = java.nio.file.Files.newBufferedReader(path, java.nio.charset.StandardCharsets.UTF_8)) {
    return reader.lines().toList();
}
// 等价于 finally 里调用 close()，且能正确抑制异常
```

### 显式字符集

```java
// 错误：依赖平台默认编码，Windows 上是 GBK，换机器就乱码
var text = java.nio.file.Files.readString(path);
// 正确
var text2 = java.nio.file.Files.readString(path, java.nio.charset.StandardCharsets.UTF_8);
```

### 自定义异常

```java
public class ConfigException extends RuntimeException {
    public ConfigException(String message, Throwable cause) { super(message, cause); }
}
```

## 常见坑清单

- 吞异常：`catch (Exception e) {}` 让 bug 消失而不是被发现
- 在 finally 里 return，会覆盖 try 里的返回值
- 用异常做流程控制（性能差且可读性差）
- 包装异常时丢掉 cause，堆栈断链

## 练习

**练习 1**：写一个方法读取 UTF-8 文本文件，文件不存在时返回空列表而不是抛异常，其它 IO 错误照常抛出。
- 验收标准：用 `NoSuchFileException` 精确捕获；不要 `catch (Exception)`。

**练习 2**：把一段用 `try/finally` 手动关流的代码改写成 try-with-resources。
- 验收标准：改写后代码更短，且异常抑制行为正确（可以说明 suppressed 的含义）。

**练习 3**：设计一个 `parseAge(String)`：空值返回 `Optional.empty()`，非法数字抛 `IllegalArgumentException` 并带上原始输入。
- 验收标准：异常消息包含原始输入；不吞掉 `NumberFormatException` 的 cause。
