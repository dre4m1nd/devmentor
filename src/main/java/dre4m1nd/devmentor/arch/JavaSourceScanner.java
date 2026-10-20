package dre4m1nd.devmentor.arch;

import com.sun.source.tree.ClassTree;
import com.sun.source.tree.CompilationUnitTree;
import com.sun.source.tree.ImportTree;
import com.sun.source.tree.MethodTree;
import com.sun.source.tree.Tree;
import com.sun.source.tree.VariableTree;
import com.sun.source.util.JavacTask;
import com.sun.source.util.SourcePositions;
import com.sun.source.util.TreeScanner;
import com.sun.source.util.Trees;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.stream.Stream;
import javax.tools.JavaCompiler;
import javax.tools.JavaFileObject;
import javax.tools.SimpleJavaFileObject;
import javax.tools.StandardJavaFileManager;
import javax.tools.ToolProvider;

/**
 * 用 JDK 自带的 javac 语法树解析 Java 源码，产出结构化事实。
 *
 * <p>刻意**不做**语义分析（不解析类型、不建符号表）：架构评审只需要结构信息，而完整编译要求
 * 依赖齐全、构建可跑。语法树解析对任何能编译的源码都成立，且不需要 classpath。
 */
public final class JavaSourceScanner {

    private JavaSourceScanner() {}

    /** 扫描项目下所有 .java 文件（跳过构建产物与隐藏目录）。 */
    public static List<SourceFileInfo> scan(Path root, Set<String> excludedDirs, int maxFiles)
            throws IOException {
        List<Path> files;
        try (Stream<Path> stream = Files.walk(root)) {
            files =
                    stream.filter(Files::isRegularFile)
                            .filter(p -> p.toString().toLowerCase(Locale.ROOT).endsWith(".java"))
                            .filter(p -> !isExcluded(root.relativize(p), excludedDirs))
                            .sorted()
                            .limit(maxFiles)
                            .toList();
        }

        JavaCompiler compiler = ToolProvider.getSystemJavaCompiler();
        if (compiler == null) {
            throw new IllegalStateException("当前 JVM 没有 javac（需要 JDK 而不是 JRE）。");
        }

        List<SourceFileInfo> result = new ArrayList<>();
        for (Path file : files) {
            try {
                SourceFileInfo info = parse(compiler, root, file);
                if (info != null) {
                    result.add(info);
                }
            } catch (Exception e) {
                // 语法错误、超时、未知字符都会落在这里。扫描已尽力而为：跳过坏文件、
                // 继续扫描其余文件，而不是让整次评审失败。
            }
        }
        return result;
    }

    private static boolean isExcluded(Path relative, Set<String> excludedDirs) {
        for (Path part : relative) {
            String name = part.toString();
            if (excludedDirs.contains(name)) {
                return true;
            }
            if (name.startsWith(".") && !name.equals(".")) {
                return true;
            }
        }
        return false;
    }

    private static SourceFileInfo parse(JavaCompiler compiler, Path root, Path file)
            throws IOException {
        String source = Files.readString(file, StandardCharsets.UTF_8);
        String relative = root.relativize(file).toString().replace('\\', '/');

        try (StandardJavaFileManager fm =
                compiler.getStandardFileManager(null, Locale.getDefault(), StandardCharsets.UTF_8)) {
            // 必须把真实文件交给 javac：用 string:/// URI 构造的 JavaFileObject 拿不到
            // 源码位置（SourcePositions 返回 -1），maxMethodLines 计算会 NPE。
            JavacTask task =
                    (JavacTask)
                            compiler.getTask(
                                    null,
                                    fm,
                                    null,
                                    List.of("-proc:none", "-encoding", "UTF-8"),
                                    null,
                                    fm.getJavaFileObjectsFromFiles(List.of(file.toFile())));
            for (CompilationUnitTree cu : task.parse()) {
                return collect(cu, source, relative, task);
            }
        }
        return null;
    }

    private static SourceFileInfo collect(
            CompilationUnitTree cu, String source, String relative, JavacTask task) {
        SourcePositions positions = Trees.instance(task).getSourcePositions();
        Set<String> imports = new LinkedHashSet<>();
        for (ImportTree it : cu.getImports()) {
            imports.add(it.getQualifiedIdentifier().toString());
        }

        String pkg = cu.getPackageName() == null ? "" : cu.getPackageName().toString();

        Counter counter = new Counter(cu, positions, source);
        String topType = "";
        for (Tree decl : cu.getTypeDecls()) {
            if (decl instanceof ClassTree ct) {
                if (topType.isEmpty()) {
                    topType = ct.getSimpleName().toString();
                }
                counter.scan(decl, null);
            }
        }

        return new SourceFileInfo(
                relative,
                pkg,
                topType,
                List.copyOf(imports),
                (int) source.lines().count(),
                counter.methods,
                counter.fields,
                counter.publicMethods,
                counter.maxMethodLines,
                countCommentLines(source),
                counter.hasJavadoc || source.contains("/**"));
    }

    private static int countCommentLines(String source) {
        int count = 0;
        for (String line : source.split("\n", -1)) {
            String trimmed = line.strip();
            if (trimmed.startsWith("//")
                    || trimmed.startsWith("/*")
                    || trimmed.startsWith("*")) {
                count++;
            }
        }
        return count;
    }

    /** 遍历语法树，统计方法/字段/最长方法行数。 */
    private static final class Counter extends TreeScanner<Void, Void> {
        private final CompilationUnitTree unit;
        private final SourcePositions positions;
        private final String source;
        private final int[] lineStarts;

        int methods;
        int fields;
        int publicMethods;
        int maxMethodLines;
        boolean hasJavadoc;

        Counter(CompilationUnitTree unit, SourcePositions positions, String source) {
            this.unit = unit;
            this.positions = positions;
            this.source = source;
            List<Integer> starts = new ArrayList<>();
            starts.add(0);
            for (int i = 0; i < source.length(); i++) {
                if (source.charAt(i) == '\n') {
                    starts.add(i + 1);
                }
            }
            this.lineStarts = starts.stream().mapToInt(Integer::intValue).toArray();
        }

        @Override
        public Void visitMethod(MethodTree node, Void unused) {
            methods++;
            String mods = node.getModifiers().toString();
            if (mods.contains("public")) {
                publicMethods++;
            }
            long start = positions.getStartPosition(unit, node);
            long end = positions.getEndPosition(unit, node);
            if (start >= 0 && end > start) {
                int lines = lineOf((int) end) - lineOf((int) start) + 1;
                maxMethodLines = Math.max(maxMethodLines, lines);
            }
            return super.visitMethod(node, unused);
        }

        @Override
        public Void visitVariable(VariableTree node, Void unused) {
            Tree parent = null;
            fields++;
            return super.visitVariable(node, unused);
        }

        private int lineOf(int offset) {
            int lo = 0;
            int hi = lineStarts.length - 1;
            while (lo < hi) {
                int mid = (lo + hi + 1) >>> 1;
                if (lineStarts[mid] <= offset) {
                    lo = mid;
                } else {
                    hi = mid - 1;
                }
            }
            return lo;
        }
    }
}
