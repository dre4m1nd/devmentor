package dre4m1nd.devmentor.arch;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * 确定性的架构规则检查。
 *
 * <p>设计原则：**只报能给出具体证据的问题**。宁可少报，也不要产出"建议使用设计模式"
 * 这类无法验证的空话——那种输出对用户毫无价值，也正是纯 LLM 评审的通病。
 *
 * <p>每条规则都能用数字或文件路径证明，用户可以自己去核对。
 */
public final class ArchitectureRules {

    /** 单文件行数超过此值视为"上帝类"候选。 */
    static final int GOD_CLASS_LINES = 600;

    /** 单个方法行数超过此值视为过长。 */
    static final int LONG_METHOD_LINES = 80;

    /** 单文件方法数超过此值视为职责过多。 */
    static final int TOO_MANY_METHODS = 25;

    /** 平均每个方法少于此行数则视为纯访问器（POJO），不按「职责过多」报告。 */
    static final int MIN_AVG_METHOD_LINES = 8;

    /** 包内文件数超过此值视为缺少分层。 */
    static final int FLAT_PACKAGE_FILES = 20;

    private ArchitectureRules() {}

    /** 跑全部规则，按严重程度排序返回。 */
    public static List<ArchFinding> check(ProjectSnapshot snapshot) {
        List<ArchFinding> findings = new ArrayList<>();
        checkGodClasses(snapshot, findings);
        checkLongMethods(snapshot, findings);
        checkTooManyMethods(snapshot, findings);
        checkFlatPackages(snapshot, findings);
        checkCycles(snapshot, findings);
        checkLayerViolations(snapshot, findings);
        checkNoTests(snapshot, findings);
        checkNoComments(snapshot, findings);
        checkMixedPackageRoots(snapshot, findings);

        findings.sort(
                Comparator.comparing((ArchFinding f) -> f.severity().ordinal())
                        .thenComparing(ArchFinding::rule));
        return findings;
    }

    // ------------------------------------------------------------ 规则实现

    private static void checkGodClasses(ProjectSnapshot snapshot, List<ArchFinding> out) {
        for (SourceFileInfo f : snapshot.files()) {
            if (f.lineCount() > GOD_CLASS_LINES && !ProjectSnapshot.isTestFile(f)) {
                out.add(
                        new ArchFinding(
                                "god-class",
                                ArchFinding.Severity.HIGH,
                                "类体量过大，职责很可能不单一：" + f.typeName(),
                                f.path() + " 共 " + f.lineCount() + " 行、" + f.methods() + " 个方法",
                                "按变化原因拆分：把数据访问、业务规则、外部调用分成不同类；"
                                        + "先抽出最独立的那一块，保持每步可编译。",
                                List.of(f.path())));
            }
        }
    }

    private static void checkLongMethods(ProjectSnapshot snapshot, List<ArchFinding> out) {
        for (SourceFileInfo f : snapshot.files()) {
            if (f.maxMethodLines() > LONG_METHOD_LINES && !ProjectSnapshot.isTestFile(f)) {
                out.add(
                        new ArchFinding(
                                "long-method",
                                ArchFinding.Severity.MEDIUM,
                                "存在超长方法：" + f.typeName(),
                                f.path() + " 最长方法约 " + f.maxMethodLines() + " 行",
                                "超过 80 行的方法通常混了多个抽象层次；"
                                        + "按「读取→校验→计算→写回」切段，每段提炼成有名字的方法。",
                                List.of(f.path())));
            }
        }
    }

    private static void checkTooManyMethods(ProjectSnapshot snapshot, List<ArchFinding> out) {
        for (SourceFileInfo f : snapshot.files()) {
            if (f.methods() <= TOO_MANY_METHODS || ProjectSnapshot.isTestFile(f)) {
                continue;
            }
            // 过滤器：平均行长很短说明这是一堆 getter/setter（纯 POJO），不是「多个角色」。
            // 不滤掉的话，每个配置/实体类都会命中，报告里 17% 是噪音。
            int avgLines = f.lineCount() / Math.max(1, f.methods());
            if (avgLines < MIN_AVG_METHOD_LINES) {
                continue;
            }
            out.add(
                    new ArchFinding(
                            "many-methods",
                            ArchFinding.Severity.MEDIUM,
                            "方法数量过多，可能承担了多个角色：" + f.typeName(),
                            f.path()
                                    + " 共 "
                                    + f.methods()
                                    + " 个方法，平均每方法约 "
                                    + avgLines
                                    + " 行",
                            "看看方法名里是否反复出现不同领域的名词（如 order* 与 user*），"
                                    + "若出现，按领域拆类。",
                            List.of(f.path())));
        }
    }

    private static void checkFlatPackages(ProjectSnapshot snapshot, List<ArchFinding> out) {
        Map<String, List<SourceFileInfo>> byPackage = snapshot.byPackage();
        for (Map.Entry<String, List<SourceFileInfo>> e : byPackage.entrySet()) {
            String pkg = e.getKey();
            List<SourceFileInfo> files = e.getValue();
            if (files.size() >= FLAT_PACKAGE_FILES && isLeafPackage(byPackage, pkg)) {
                out.add(
                        new ArchFinding(
                                "flat-package",
                                ArchFinding.Severity.MEDIUM,
                                "包内平铺过多类，缺少子领域划分："
                                        + (pkg.isBlank() ? "(默认包)" : pkg),
                                "该包下直接有 " + files.size() + " 个类，且没有子包",
                                "按职责拆子包（如 domain / application / infrastructure，"
                                        + "或按业务子域拆分），避免一个包同时容纳实体、服务和适配器。",
                                files.stream().map(SourceFileInfo::path).limit(8).toList()));
            }
        }
    }

    private static boolean isLeafPackage(Map<String, List<SourceFileInfo>> byPackage, String pkg) {
        String prefix = pkg.isEmpty() ? "" : pkg + ".";
        return byPackage.keySet().stream()
                .noneMatch(other -> !other.equals(pkg) && other.startsWith(prefix) && !prefix.isEmpty());
    }

    private static void checkCycles(ProjectSnapshot snapshot, List<ArchFinding> out) {
        Map<String, Set<String>> graph = snapshot.packageDependencies();
        List<List<String>> cycles = findCycles(graph, 12);
        for (List<String> cycle : cycles) {
            out.add(
                    new ArchFinding(
                            "package-cycle",
                            ArchFinding.Severity.HIGH,
                            "包之间存在循环依赖",
                            String.join(" → ", cycle),
                            "循环依赖让两个包无法独立理解、独立测试。"
                                    + "常见解法：把双方共同依赖的部分抽成第三个包；"
                                    + "或把其中一侧的调用改为事件/接口回调。",
                            List.of()));
        }
    }

    /** 用 DFS 找出长度不超过 maxLength 的环（去重：只保留起点最小的那个表示）。 */
    static List<List<String>> findCycles(Map<String, Set<String>> graph, int maxLength) {
        List<List<String>> found = new ArrayList<>();
        Set<String> seen = new HashSet<>();
        for (String start : graph.keySet()) {
            dfs(graph, start, start, new ArrayList<>(List.of(start)), new HashSet<>(), found, seen, maxLength);
        }
        return found;
    }

    private static void dfs(
            Map<String, Set<String>> graph,
            String start,
            String current,
            List<String> path,
            Set<String> onPath,
            List<List<String>> found,
            Set<String> seen,
            int maxLength) {
        if (path.size() > maxLength) {
            return;
        }
        onPath.add(current);
        for (String next : graph.getOrDefault(current, Set.of())) {
            if (next.equals(start) && path.size() > 1) {
                // 只保留以最小节点开头的环，避免重复
                String min = path.stream().min(String::compareTo).orElse(start);
                if (min.equals(start)) {
                    List<String> cycle = new ArrayList<>(path);
                    cycle.add(start);
                    String key = String.join(">", cycle);
                    if (seen.add(key)) {
                        found.add(cycle);
                    }
                }
            } else if (!onPath.contains(next) && next.compareTo(start) >= 0) {
                path.add(next);
                dfs(graph, start, next, path, onPath, found, seen, maxLength);
                path.remove(path.size() - 1);
            }
        }
        onPath.remove(current);
    }

    private static void checkLayerViolations(ProjectSnapshot snapshot, List<ArchFinding> out) {

        // 常见分层：controller/web → service → repository/dao。反向依赖即为违规。
        Map<String, List<String>> violations = new HashMap<>();
        Map<String, Set<String>> graph = snapshot.packageDependencies();
        for (Map.Entry<String, Set<String>> e : graph.entrySet()) {
            String from = e.getKey();
            String fromLayer = layerOf(from);
            if (fromLayer == null) {
                continue;
            }
            for (String to : e.getValue()) {
                String toLayer = layerOf(to);
                if (toLayer == null || toLayer.equals(fromLayer)) {
                    continue;
                }
                // 反向依赖才算违规：下层（repository，rank 1）依赖上层（service，rank 2）
                // 是分层倒置；上层依赖下层是正常方向。
                if (layerRank(toLayer) > layerRank(fromLayer)) {
                    violations
                            .computeIfAbsent(from + " -> " + to, k -> new ArrayList<>())
                            .add(fromLayer + " 依赖 " + toLayer);
                }
            }
        }
        for (Map.Entry<String, List<String>> e : violations.entrySet()) {
            out.add(
                    new ArchFinding(
                            "layer-violation",
                            ArchFinding.Severity.HIGH,
                            "分层方向被违反",
                            e.getKey() + "（" + e.getValue().get(0) + "）",
                            "下层不应知道上层：把 repository 需要的逻辑下沉到 service，"
                                    + "或者由上层把已经算好的数据作为参数传给 repository。",
                            List.of()));
        }
    }

    private static String layerOf(String pkg) {
        String lower = pkg.toLowerCase();
        if (lower.endsWith(".controller") || lower.endsWith(".web") || lower.endsWith(".api")) {
            return "controller";
        }
        if (lower.endsWith(".service") || lower.endsWith(".application")) {
            return "service";
        }
        if (lower.endsWith(".repository")
                || lower.endsWith(".dao")
                || lower.endsWith(".mapper")
                || lower.endsWith(".infrastructure")) {
            return "repository";
        }
        return null;
    }

    private static int layerRank(String layer) {
        return switch (layer) {
            case "controller" -> 3;
            case "service" -> 2;
            default -> 1;
        };
    }

    private static void checkNoTests(ProjectSnapshot snapshot, List<ArchFinding> out) {
        if (snapshot.fileCount() >= 10 && snapshot.testFileCount() == 0) {
            out.add(
                    new ArchFinding(
                            "no-tests",
                            ArchFinding.Severity.HIGH,
                            "项目里没有任何测试类",
                            "扫描到 " + snapshot.fileCount() + " 个源文件，测试文件 0 个",
                            "先给最核心的一两个纯函数补测试，能跑起来再谈覆盖率；"
                                    + "没有测试的架构改动风险不可控。",
                            List.of()));
        }
    }

    private static void checkNoComments(ProjectSnapshot snapshot, List<ArchFinding> out) {
        long undocumented =
                snapshot.files().stream()
                        .filter(f -> !ProjectSnapshot.isTestFile(f))
                        .filter(f -> f.lineCount() > 100)
                        .filter(f -> f.commentLines() == 0)
                        .count();
        if (undocumented >= 3) {
            out.add(
                    new ArchFinding(
                            "no-comments",
                            ArchFinding.Severity.LOW,
                            "多个较大的类没有任何注释",
                            undocumented + " 个超过 100 行的类注释行数为 0",
                            "不需要逐行注释；至少在每个公开类的顶部写清「它负责什么、不负责什么」，"
                                    + "这比方法内注释更有价值。",
                            snapshot.files().stream()
                                    .filter(f -> !ProjectSnapshot.isTestFile(f))
                                    .filter(f -> f.lineCount() > 100 && f.commentLines() == 0)
                                    .map(SourceFileInfo::path)
                                    .limit(5)
                                    .toList()));
        }
    }

    private static void checkMixedPackageRoots(ProjectSnapshot snapshot, List<ArchFinding> out) {
        Set<String> roots = new LinkedHashSet<>();
        for (SourceFileInfo f : snapshot.files()) {
            String pkg = f.packageName();
            if (pkg.isBlank()) {
                roots.add("(默认包)");
            } else {
                roots.add(pkg.split("\\.")[0]);
            }
        }
        if (roots.size() > 1) {
            out.add(
                    new ArchFinding(
                            "mixed-roots",
                            ArchFinding.Severity.LOW,
                            "存在多个顶层包根，命名空间不统一",
                            String.join(", ", roots),
                            "统一到一个反向域名根（如 com.yourcompany.project）下，"
                                    + "否则 IDE 的包视图和依赖分析都会变乱。",
                            List.of()));
        }
    }
}
