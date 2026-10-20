package dre4m1nd.devmentor.arch;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import java.util.stream.Stream;

/**
 * 架构评审的入口：扫描 → 聚合 → 规则检查 → 生成给模型的报告。
 *
 * <p>产出的报告是**纯文本事实**，模型据此给出判断与优先级建议，而不是让它凭印象猜项目长什么样。
 */
public final class ArchitectureAnalyzer {

    /** 默认跳过的目录：构建产物、IDE、依赖缓存。 */
    public static final Set<String> DEFAULT_EXCLUDED =
            Set.of("target", "build", "out", "bin", "node_modules", ".git", ".idea", ".mvn", "dist");

    static final int MAX_FILES = 2000;
    private static final int MAX_LISTED_FILES = 25;

    private ArchitectureAnalyzer() {}

    /** 扫描并检查。 */
    public static Result analyze(Path projectRoot) throws IOException {
        return analyze(projectRoot, DEFAULT_EXCLUDED);
    }

    public static Result analyze(Path projectRoot, Set<String> excluded) throws IOException {
        if (!Files.isDirectory(projectRoot)) {
            throw new IllegalArgumentException("不是有效目录: " + projectRoot);
        }
        List<SourceFileInfo> files = JavaSourceScanner.scan(projectRoot, excluded, MAX_FILES);
        ProjectSnapshot snapshot = new ProjectSnapshot(files);
        List<ArchFinding> findings = ArchitectureRules.check(snapshot);
        return new Result(snapshot, findings, projectRoot);
    }

    /** 分析结果。 */
    public record Result(ProjectSnapshot snapshot, List<ArchFinding> findings, Path projectRoot) {

        public boolean isEmpty() {
            return snapshot.fileCount() == 0;
        }

        public long countOf(ArchFinding.Severity severity) {
            return findings.stream().filter(f -> f.severity() == severity).count();
        }

        /** 生成给模型阅读的紧凑报告。 */
        public String render() {
            StringBuilder sb = new StringBuilder();
            ProjectSnapshot s = snapshot;

            sb.append("# 项目架构事实（静态分析，非推测）\n\n");
            sb.append("- 根目录: ").append(projectRoot).append('\n');
            sb.append("- 根包: ").append(s.rootPackage().isBlank() ? "(无/默认包)" : s.rootPackage()).append('\n');
            sb.append("- 源文件: ").append(s.fileCount()).append(" 个（测试 ")
                    .append(s.testFileCount()).append(" 个）\n");
            sb.append("- 总行数: ").append(s.totalLines()).append('\n');
            sb.append("- 方法总数: ").append(s.totalMethods()).append("\n\n");

            sb.append("## 包结构\n");
            s.byPackage().forEach((pkg, list) ->
                    sb.append("- ").append(pkg.isBlank() ? "(默认包)" : pkg)
                            .append("  [").append(list.size()).append(" 个类]\n"));
            sb.append('\n');

            sb.append("## 包级依赖\n");
            var graph = s.packageDependencies();
            if (graph.isEmpty()) {
                sb.append("(无项目内部跨包依赖)\n");
            } else {
                graph.forEach((from, tos) -> {
                    if (!tos.isEmpty()) {
                        sb.append("- ").append(from).append(" → ")
                                .append(String.join(", ", tos)).append('\n');
                    }
                });
            }
            sb.append('\n');

            sb.append("## 体量最大的文件\n");
            for (SourceFileInfo f : s.largestFiles(10)) {
                sb.append("- ").append(f.path())
                        .append("  ").append(f.lineCount()).append(" 行 / ")
                        .append(f.methods()).append(" 方法 / 最长方法 ")
                        .append(f.maxMethodLines()).append(" 行\n");
            }
            sb.append('\n');

            sb.append("## 规则检查结果\n");
            if (findings.isEmpty()) {
                sb.append("未发现规则可判定的问题。\n");
            } else {
                sb.append("共 ").append(findings.size()).append(" 条：高 ")
                        .append(countOf(ArchFinding.Severity.HIGH)).append(" / 中 ")
                        .append(countOf(ArchFinding.Severity.MEDIUM)).append(" / 低 ")
                        .append(countOf(ArchFinding.Severity.LOW)).append("\n\n");
                for (ArchFinding f : findings) {
                    sb.append("- ").append(f.render()).append('\n');
                }
            }
            return sb.toString();
        }

        /** 报告落盘（供 CLI 展示与后续追问引用）。 */
        public Path writeReport(Path dir) throws IOException {
            Files.createDirectories(dir);
            Path file = dir.resolve("architecture-report.md");
            Files.writeString(file, render());
            return file;
        }
    }

    /** 供 CLI 列表用：项目里前 N 个源文件。 */
    public static List<String> listSources(Path projectRoot, int limit) throws IOException {
        if (!Files.isDirectory(projectRoot)) {
            return List.of();
        }
        List<String> result = new ArrayList<>();
        try (Stream<Path> stream = Files.walk(projectRoot)) {
            stream.filter(Files::isRegularFile)
                    .filter(p -> p.toString().endsWith(".java"))
                    .filter(p -> {
                        for (Path part : projectRoot.relativize(p)) {
                            if (DEFAULT_EXCLUDED.contains(part.toString())
                                    || part.toString().startsWith(".")) {
                                return false;
                            }
                        }
                        return true;
                    })
                    .sorted()
                    .limit(limit)
                    .forEach(p -> result.add(projectRoot.relativize(p).toString().replace('\\', '/')));
        }
        return result;
    }

    static int maxListedFiles() {
        return MAX_LISTED_FILES;
    }
}
