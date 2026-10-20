package dre4m1nd.devmentor.tools;

import io.agentscope.core.tool.Tool;
import io.agentscope.core.tool.ToolParam;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.charset.Charset;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;
import java.util.concurrent.TimeUnit;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import javax.tools.Diagnostic;
import javax.tools.DiagnosticCollector;
import javax.tools.JavaCompiler;
import javax.tools.JavaFileObject;
import javax.tools.StandardJavaFileManager;
import javax.tools.ToolProvider;

/**
 * 让智能体真正编译、运行 Java 片段的教学工具。
 *
 * <p>工具实例无状态：每次调用都新建临时目录，用完即删，因此可被并发共享。
 */
public class JavaSnippetTools {

    /** 匹配 {@code public class/record/interface/enum Name}。 */
    private static final Pattern PUBLIC_TYPE =
            Pattern.compile(
                    "\\bpublic\\s+(?:final\\s+|abstract\\s+|sealed\\s+|non-sealed\\s+)*"
                            + "(?:class|record|interface|enum)\\s+([A-Za-z_$][A-Za-z0-9_$]*)");

    /** 匹配任意顶层类型声明（不含 public 时也能定名）。 */
    private static final Pattern ANY_TYPE =
            Pattern.compile(
                    "(?:^|[;}\\s])(?:final\\s+|abstract\\s+|sealed\\s+|non-sealed\\s+)*"
                            + "(?:class|record|interface|enum)\\s+([A-Za-z_$][A-Za-z0-9_$]*)",
                    Pattern.MULTILINE);
    private static final int MAX_OUTPUT_CHARS = 8000;

    private final int timeoutSeconds;
    private final int maxSourceChars;

    public JavaSnippetTools(int timeoutSeconds, int maxSourceChars) {
        this.timeoutSeconds = timeoutSeconds > 0 ? timeoutSeconds : 10;
        this.maxSourceChars = maxSourceChars > 0 ? maxSourceChars : 20000;
    }

    @Tool(
            name = "java_compile_check",
            readOnly = true,
            description =
                    "Compile a Java source snippet with the JDK compiler and report diagnostics"
                        + " (file:line:column plus the message). Does not execute anything."
                        + " Use it to verify code you are about to show the learner.")
    public String javaCompileCheck(
            @ToolParam(name = "source", description = "完整可编译的 Java 源码") String source) {
        String problem = validateSource(source);
        if (problem != null) {
            return problem;
        }
        Path dir = null;
        try {
            dir = Files.createTempDirectory("devmentor-check-");
            Path file = writeSource(dir, source);
            CompilationOutcome outcome = compile(file, dir);
            if (outcome.success) {
                return "编译通过 ✅（" + file.getFileName() + "）";
            }
            return "编译失败 ❌\n" + outcome.diagnostics;
        } catch (IOException e) {
            return "无法准备编译环境: " + e.getMessage();
        } finally {
            deleteQuietly(dir);
        }
    }

    @Tool(
            name = "java_run_snippet",
            readOnly = false,
            concurrencySafe = false,
            description =
                    "Compile and actually run a Java snippet in a temp directory, returning exit"
                        + " code, stdout and stderr. Use it whenever you claim code works: the"
                        + " learner should see real output, not a guess.")
    public String javaRunSnippet(
            @ToolParam(name = "source", description = "完整可运行的 Java 源码，含 main 方法")
                    String source,
            @ToolParam(
                            name = "stdin",
                            description = "可选的标准输入内容，按行喂给程序",
                            required = false)
                    String stdin) {
        String problem = validateSource(source);
        if (problem != null) {
            return problem;
        }
        Path dir = null;
        try {
            dir = Files.createTempDirectory("devmentor-run-");
            Path file = writeSource(dir, source);
            CompilationOutcome outcome = compile(file, dir);
            if (!outcome.success) {
                return "编译失败 ❌\n" + outcome.diagnostics;
            }
            String className = mainClassName(source, file);
            return run(dir, className, stdin);
        } catch (IOException e) {
            return "无法准备运行环境: " + e.getMessage();
        } finally {
            deleteQuietly(dir);
        }
    }

    // ---------------------------------------------------------------- helpers

    private String validateSource(String source) {
        if (source == null || source.isBlank()) {
            return "源码为空，请提供完整的 Java 代码。";
        }
        if (source.length() > maxSourceChars) {
            return "源码过长（" + source.length() + " 字符，上限 " + maxSourceChars + "）。请精简后再试。";
        }
        if (ToolProvider.getSystemJavaCompiler() == null) {
            return "当前 JVM 没有可用的 Java 编译器（需要 JDK 而不是 JRE）。请改用 JDK 17 启动。";
        }
        return null;
    }

    /**
     * 把源码写入临时文件。
     *
     * <p>文件名必须与 {@code public} 类型名一致，否则 javac 会直接拒绝（"类 X 是公共的，应在
     * 名为 X.java 的文件中声明"）。没有 public 类型时退回 {@code Snippet.java}。
     */
    private Path writeSource(Path dir, String source) throws IOException {
        Path file = dir.resolve(fileNameFor(source));
        Files.writeString(file, source, StandardCharsets.UTF_8);
        return file;
    }

    /** 推断源文件应有的文件名：优先取 public 类型名，其次取第一个类型名。 */
    static String fileNameFor(String source) {
        Matcher publicType = PUBLIC_TYPE.matcher(source);
        if (publicType.find()) {
            return publicType.group(1) + ".java";
        }
        Matcher anyType = ANY_TYPE.matcher(source);
        if (anyType.find()) {
            return anyType.group(1) + ".java";
        }
        return "Snippet.java";
    }

    private record CompilationOutcome(boolean success, String diagnostics) {}

    private CompilationOutcome compile(Path file, Path outDir) throws IOException {
        JavaCompiler compiler = ToolProvider.getSystemJavaCompiler();
        DiagnosticCollector<JavaFileObject> diagnostics = new DiagnosticCollector<>();
        try (StandardJavaFileManager manager =
                compiler.getStandardFileManager(diagnostics, Locale.getDefault(), StandardCharsets.UTF_8)) {
            Iterable<? extends JavaFileObject> units =
                    manager.getJavaFileObjectsFromFiles(List.of(file.toFile()));
            List<String> options = List.of("-d", outDir.toString(), "-encoding", "UTF-8");
            boolean ok =
                    compiler.getTask(null, manager, diagnostics, options, null, units).call();
            if (ok) {
                return new CompilationOutcome(true, "");
            }
            return new CompilationOutcome(false, formatDiagnostics(diagnostics));
        }
    }

    private String formatDiagnostics(DiagnosticCollector<JavaFileObject> diagnostics) {
        StringBuilder sb = new StringBuilder();
        for (Diagnostic<? extends JavaFileObject> d : diagnostics.getDiagnostics()) {
            sb.append("- ");
            if (d.getLineNumber() > 0) {
                sb.append("第 ").append(d.getLineNumber()).append(" 行");
                if (d.getColumnNumber() > 0) {
                    sb.append("，第 ").append(d.getColumnNumber()).append(" 列");
                }
                sb.append("：");
            }
            sb.append(d.getMessage(Locale.getDefault())).append('\n');
        }
        return sb.isEmpty() ? "（编译器未返回诊断信息）" : sb.toString();
    }

    /** 主类名：与源文件名一致（已由 {@link #fileNameFor(String)} 保证含 main 的类型优先）。 */
    private String mainClassName(String source, Path file) {
        String fileName = file.getFileName().toString();
        return fileName.substring(0, fileName.length() - ".java".length());
    }

    private String run(Path dir, String className, String stdin) {
        Path java = javaExecutable();
        if (java == null) {
            return "找不到 java 可执行文件（" + System.getProperty("java.home") + "）。";
        }
        ProcessBuilder pb =
                new ProcessBuilder(java.toString(), "-Dfile.encoding=UTF-8", "-cp", dir.toString(), className);
        pb.directory(dir.toFile());
        pb.redirectErrorStream(false);

        long startedAt = System.nanoTime();
        Process process;
        try {
            process = pb.start();
        } catch (IOException e) {
            return "无法启动 JVM: " + e.getMessage();
        }

        try (OutputStream os = process.getOutputStream()) {
            if (stdin != null && !stdin.isEmpty()) {
                os.write(stdin.getBytes(StandardCharsets.UTF_8));
                if (!stdin.endsWith("\n")) {
                    os.write('\n');
                }
            }
        } catch (IOException ignored) {
            // 程序可能不读 stdin，提前关闭即可
        }

        ByteArrayOutputStream stdout = new ByteArrayOutputStream();
        ByteArrayOutputStream stderr = new ByteArrayOutputStream();
        Thread outDrain = drain(process.getInputStream(), stdout);
        Thread errDrain = drain(process.getErrorStream(), stderr);

        boolean finished;
        try {
            finished = process.waitFor(timeoutSeconds, TimeUnit.SECONDS);
            if (!finished) {
                process.destroyForcibly();
                process.waitFor(2, TimeUnit.SECONDS);
            }
            outDrain.join(1000);
            errDrain.join(1000);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            process.destroyForcibly();
            return "执行被中断。";
        }

        long elapsedMs = (System.nanoTime() - startedAt) / 1_000_000;
        String out = truncate(decode(stdout.toByteArray()));
        String err = truncate(decode(stderr.toByteArray()));

        StringBuilder sb = new StringBuilder();
        if (!finished) {
            sb.append("超时终止 ⏱ 超过 ").append(timeoutSeconds).append(" 秒（可能是死循环）\n");
        } else {
            sb.append("退出码: ").append(process.exitValue()).append("（耗时 ").append(elapsedMs).append(" ms）\n");
        }
        sb.append("--- 标准输出 ---\n").append(out.isEmpty() ? "(空)" : out).append('\n');
        if (!err.isEmpty()) {
            sb.append("--- 标准错误 ---\n").append(err).append('\n');
        }
        return sb.toString();
    }

    private static Path javaExecutable() {
        Path bin = Path.of(System.getProperty("java.home"), "bin");
        List<Path> candidates = new ArrayList<>();
        candidates.add(bin.resolve("java"));
        candidates.add(bin.resolve("java.exe"));
        for (Path candidate : candidates) {
            if (Files.isExecutable(candidate) || Files.isRegularFile(candidate)) {
                return candidate;
            }
        }
        return null;
    }

    private static Thread drain(InputStream in, ByteArrayOutputStream sink) {
        Thread thread =
                new Thread(
                        () -> {
                            byte[] buffer = new byte[4096];
                            try (InputStream is = in) {
                                int read;
                                while ((read = is.read(buffer)) != -1) {
                                    synchronized (sink) {
                                        if (sink.size() < 1_000_000) {
                                            sink.write(buffer, 0, read);
                                        }
                                    }
                                }
                            } catch (IOException ignored) {
                                // 进程被杀时流会关闭，忽略
                            }
                        });
        thread.setDaemon(true);
        thread.start();
        return thread;
    }

    /**
     * 解码子进程输出。
     *
     * <p>子进程是用 {@code -Dfile.encoding=UTF-8} 启动的，所以优先按 UTF-8 严格解码；
     * 只有当字节不是合法 UTF-8 时才退回平台默认字符集（例如老代码自己按 GBK 打印）。
     */
    private static String decode(byte[] bytes) {
        try {
            var decoder =
                    StandardCharsets.UTF_8
                            .newDecoder()
                            .onMalformedInput(java.nio.charset.CodingErrorAction.REPORT)
                            .onUnmappableCharacter(java.nio.charset.CodingErrorAction.REPORT);
            return decoder.decode(java.nio.ByteBuffer.wrap(bytes)).toString();
        } catch (java.nio.charset.CharacterCodingException e) {
            return new String(bytes, Charset.defaultCharset());
        }
    }

    private static String truncate(String text) {
        if (text == null) {
            return "";
        }
        String trimmed = text.stripTrailing();
        if (trimmed.length() <= MAX_OUTPUT_CHARS) {
            return trimmed;
        }
        return trimmed.substring(0, MAX_OUTPUT_CHARS) + "\n…（输出已截断）";
    }

    private static void deleteQuietly(Path dir) {
        if (dir == null) {
            return;
        }
        try (var paths = Files.walk(dir)) {
            paths.sorted(Comparator.reverseOrder())
                    .forEach(
                            p -> {
                                try {
                                    Files.deleteIfExists(p);
                                } catch (IOException ignored) {
                                    // 清理失败不影响结果
                                }
                            });
        } catch (IOException ignored) {
            // 同上
        }
    }
}
