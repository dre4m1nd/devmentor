package dre4m1nd.devmentor.tools;

import dre4m1nd.devmentor.arch.ArchFinding;
import dre4m1nd.devmentor.arch.ArchitectureAnalyzer;
import dre4m1nd.devmentor.arch.ProjectSnapshot;
import dre4m1nd.devmentor.arch.SourceFileInfo;
import io.agentscope.core.tool.Tool;
import io.agentscope.core.tool.ToolParam;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Locale;

/**
 * 架构评审工具：让智能体独立读取用户项目并给出**有证据**的缺陷判断。
 *
 * <p>工具本身不做"评价"，只做确定性分析；评价交给模型，模型拿到的是一份可核对的
 * 事实清单，因此不会产出"建议使用设计模式"这种空话。
 */
public class ArchitectureTools {

    private final Path defaultProjectRoot;
    private final Path reportDir;

    public ArchitectureTools(Path defaultProjectRoot, Path reportDir) {
        this.defaultProjectRoot = defaultProjectRoot;
        this.reportDir = reportDir;
    }

    @Tool(
            name = "arch_scan",
            readOnly = true,
            description =
                    "Statically analyze a Java project and return architecture facts: package"
                        + " structure, package-level dependency graph, largest files, and a list of"
                        + " rule-based findings (god classes, cycles, layer violations, missing"
                        + " tests...). Each finding carries concrete evidence. Call this FIRST"
                        + " before giving any architecture advice.")
    public String archScan(
            @ToolParam(
                            name = "project_root",
                            description = "项目根目录；留空则用当前配置的代码目录",
                            required = false)
                    String projectRoot,
            @ToolParam(
                            name = "max_files",
                            description = "最多扫描多少个源文件（默认 2000）",
                            required = false)
                    Integer maxFiles) {
        Path root = resolveRoot(projectRoot);
        if (root == null) {
            return "目录不存在：" + projectRoot;
        }
        try {
            ArchitectureAnalyzer.Result result = ArchitectureAnalyzer.analyze(root);
            if (result.isEmpty()) {
                return "在 " + root + " 下没有找到 .java 源文件（已跳过 target/build/node_modules 等）。";
            }
            Path report = result.writeReport(reportDir);
            return result.render() + "\n---\n完整报告已写入: " + report;
        } catch (IOException e) {
            return "扫描失败：" + e.getMessage();
        }
    }

    @Tool(
            name = "arch_findings",
            readOnly = true,
            description =
                    "Return only the rule-based architecture findings, optionally filtered by"
                        + " minimum severity (HIGH/MEDIUM/LOW). Use it to focus on the most"
                        + " serious problems first.")
    public String archFindings(
            @ToolParam(
                            name = "min_severity",
                            description = "最低严重程度：HIGH / MEDIUM / LOW，默认 MEDIUM",
                            required = false)
                    String minSeverity) {
        ArchFinding.Severity min = parseSeverity(minSeverity);
        try {
            ArchitectureAnalyzer.Result result = ArchitectureAnalyzer.analyze(defaultProjectRoot);
            List<ArchFinding> filtered =
                    result.findings().stream().filter(f -> f.severity().ordinal() <= min.ordinal()).toList();
            if (filtered.isEmpty()) {
                return "没有达到 " + min.label() + " 及以上严重程度的问题。";
            }
            StringBuilder sb = new StringBuilder();
            sb.append("严重程度 ≥ ").append(min.label()).append(" 的问题共 ")
                    .append(filtered.size()).append(" 条：\n\n");
            for (ArchFinding f : filtered) {
                sb.append("- ").append(f.render()).append("\n\n");
            }
            return sb.toString();
        } catch (IOException e) {
            return "扫描失败：" + e.getMessage();
        }
    }

    @Tool(
            name = "arch_dependencies",
            readOnly = true,
            description =
                    "Return the package-level dependency graph of the project, plus any dependency"
                        + " cycles. Useful to explain coupling before proposing a refactor.")
    public String archDependencies(
            @ToolParam(
                            name = "project_root",
                            description = "项目根目录；留空则用当前配置的代码目录",
                            required = false)
                    String projectRoot) {
        Path root = resolveRoot(projectRoot);
        if (root == null) {
            return "目录不存在：" + projectRoot;
        }
        try {
            ArchitectureAnalyzer.Result result = ArchitectureAnalyzer.analyze(root);
            ProjectSnapshot s = result.snapshot();
            StringBuilder sb = new StringBuilder();
            sb.append("根包: ").append(s.rootPackage().isBlank() ? "(无)" : s.rootPackage()).append('\n');
            sb.append("包数: ").append(s.byPackage().size()).append('\n').append('\n');

            var graph = s.packageDependencies();
            if (graph.isEmpty()) {
                sb.append("没有项目内部的跨包依赖。\n");
            } else {
                sb.append("包级依赖：\n");
                graph.forEach((from, tos) -> sb.append("- ").append(from).append(" → ")
                        .append(tos.isEmpty() ? "(无)" : String.join(", ", tos)).append('\n'));
            }

            List<ArchFinding> cycles =
                    result.findings().stream().filter(f -> f.rule().equals("package-cycle")).toList();
            sb.append('\n');
            if (cycles.isEmpty()) {
                sb.append("未发现循环依赖。\n");
            } else {
                sb.append("发现 ").append(cycles.size()).append(" 个循环依赖：\n");
                for (ArchFinding c : cycles) {
                    sb.append("- ").append(c.evidence()).append('\n');
                }
            }
            return sb.toString();
        } catch (IOException e) {
            return "扫描失败：" + e.getMessage();
        }
    }

    @Tool(
            name = "arch_file_profile",
            readOnly = true,
            description =
                    "Profile a single Java file: size, method count, longest method, imports, and"
                        + " whether it participates in any rule violation. Use it after arch_scan to"
                        + " dig into one suspicious class.")
    public String archFileProfile(
            @ToolParam(name = "path", description = "相对项目根的源文件路径") String path) {
        if (path == null || path.isBlank()) {
            return "缺少参数 path。";
        }
        String normalized = path.trim().replace('\\', '/');
        if (normalized.contains("..")) {
            return "非法路径：" + path;
        }
        try {
            ArchitectureAnalyzer.Result result = ArchitectureAnalyzer.analyze(defaultProjectRoot);
            SourceFileInfo match =
                    result.snapshot().files().stream()
                            .filter(f -> f.path().equals(normalized) || f.path().endsWith("/" + normalized))
                            .findFirst()
                            .orElse(null);
            if (match == null) {
                return "没有找到文件 " + normalized + "。可以先用 arch_scan 看项目结构。";
            }
            StringBuilder sb = new StringBuilder();
            sb.append("文件: ").append(match.path()).append('\n');
            sb.append("类型: ").append(match.typeName()).append('\n');
            sb.append("包: ").append(match.packageName()).append('\n');
            sb.append("行数: ").append(match.lineCount()).append('\n');
            sb.append("方法数: ").append(match.methods())
                    .append("（public ").append(match.publicMethods()).append("）\n");
            sb.append("字段数: ").append(match.fields()).append('\n');
            sb.append("最长方法: ").append(match.maxMethodLines()).append(" 行\n");
            sb.append("注释行: ").append(match.commentLines()).append('\n');
            sb.append("是否测试: ").append(ProjectSnapshot.isTestFile(match) ? "是" : "否").append('\n');

            List<ArchFinding> related =
                    result.findings().stream().filter(f -> f.files().contains(match.path())).toList();
            if (related.isEmpty()) {
                sb.append("\n没有规则命中这个文件。\n");
            } else {
                sb.append("\n命中规则：\n");
                for (ArchFinding f : related) {
                    sb.append("- ").append(f.render()).append('\n');
                }
            }

            if (!match.imports().isEmpty()) {
                sb.append("\nimport 前 15 条：\n");
                match.imports().stream().limit(15).forEach(i -> sb.append("  ").append(i).append('\n'));
            }
            return sb.toString();
        } catch (IOException e) {
            return "扫描失败：" + e.getMessage();
        }
    }

    @Tool(
            name = "arch_read_source",
            readOnly = true,
            description =
                    "Read a source file from the analyzed project with line numbers, so you can"
                        + " quote the exact code you are criticizing. Supports pagination.")
    public String archReadSource(
            @ToolParam(name = "path", description = "相对项目根的源文件路径") String path,
            @ToolParam(name = "offset", description = "起始行（1 基，默认 1）", required = false)
                    Integer offset,
            @ToolParam(name = "limit", description = "读取行数（默认 200，上限 600）", required = false)
                    Integer limit) {
        if (path == null || path.isBlank()) {
            return "缺少参数 path。";
        }
        String normalized = path.trim().replace('\\', '/');
        if (normalized.contains("..") || normalized.startsWith("/")) {
            return "非法路径：" + path;
        }
        Path root = defaultProjectRoot.toAbsolutePath().normalize();
        Path file = root.resolve(normalized).normalize();
        if (!file.startsWith(root)) {
            return "非法路径：" + path;
        }
        if (!Files.isRegularFile(file)) {
            return "文件不存在：" + normalized;
        }
        try {
            List<String> lines = Files.readAllLines(file);
            int from = offset == null || offset < 1 ? 1 : offset;
            int count = limit == null || limit < 1 ? 200 : Math.min(limit, 600);
            int to = Math.min(lines.size(), from - 1 + count);
            StringBuilder sb = new StringBuilder();
            sb.append(normalized).append("（共 ").append(lines.size()).append(" 行）\n");
            for (int i = from; i <= to; i++) {
                sb.append(String.format(Locale.ROOT, "%5d | %s%n", i, lines.get(i - 1)));
            }
            if (to < lines.size()) {
                sb.append("… 还有 ").append(lines.size() - to).append(" 行，用 offset 继续读。\n");
            }
            return sb.toString();
        } catch (IOException e) {
            return "读取失败：" + e.getMessage();
        }
    }

    private Path resolveRoot(String projectRoot) {
        if (projectRoot == null || projectRoot.isBlank()) {
            return defaultProjectRoot;
        }
        Path p = Path.of(projectRoot.trim()).toAbsolutePath().normalize();
        return Files.isDirectory(p) ? p : null;
    }

    private static ArchFinding.Severity parseSeverity(String raw) {
        if (raw == null || raw.isBlank()) {
            return ArchFinding.Severity.MEDIUM;
        }
        return switch (raw.trim().toUpperCase(Locale.ROOT)) {
            case "HIGH" -> ArchFinding.Severity.HIGH;
            case "LOW" -> ArchFinding.Severity.LOW;
            default -> ArchFinding.Severity.MEDIUM;
        };
    }
}
