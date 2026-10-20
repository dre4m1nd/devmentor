package dre4m1nd.devmentor.arch;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;

/**
 * 一次项目扫描的聚合视图：包结构、依赖图、体量分布。
 *
 * <p>这是"架构事实"，不含任何判断；判断在 {@link ArchitectureRules} 里。
 */
public final class ProjectSnapshot {

    private final List<SourceFileInfo> files;
    private final String rootPackage;

    public ProjectSnapshot(List<SourceFileInfo> files) {
        this.files = List.copyOf(files);
        this.rootPackage = inferRootPackage(this.files);
    }

    /**
     * 推断项目根包：取「所有包名的公共前缀」。
     *
     * <p>例如 {@code com.acme.shop.order} 与 {@code com.acme.shop.user} → {@code com.acme.shop}。
     */
    static String inferRootPackage(List<SourceFileInfo> files) {
        List<String> packages =
                files.stream()
                        .map(SourceFileInfo::packageName)
                        .filter(p -> p != null && !p.isBlank())
                        .distinct()
                        .toList();
        if (packages.isEmpty()) {
            return "";
        }
        String[] parts = packages.get(0).split("\\.");
        int common = parts.length;
        for (String pkg : packages) {
            String[] other = pkg.split("\\.");
            int i = 0;
            while (i < common && i < other.length && parts[i].equals(other[i])) {
                i++;
            }
            common = i;
        }
        if (common == 0) {
            return "";
        }
        return String.join(".", java.util.Arrays.copyOf(parts, common));
    }

    public List<SourceFileInfo> files() {
        return files;
    }

    public String rootPackage() {
        return rootPackage;
    }

    public int fileCount() {
        return files.size();
    }

    public int totalLines() {
        return files.stream().mapToInt(SourceFileInfo::lineCount).sum();
    }

    public int totalMethods() {
        return files.stream().mapToInt(SourceFileInfo::methods).sum();
    }

    /** 包 → 该包下的文件列表（按包名排序）。 */
    public Map<String, List<SourceFileInfo>> byPackage() {
        Map<String, List<SourceFileInfo>> map = new TreeMap<>();
        for (SourceFileInfo f : files) {
            map.computeIfAbsent(f.packageName(), k -> new ArrayList<>()).add(f);
        }
        return map;
    }

    /**
     * 包级依赖图：包 A → 包 B 表示 A 里有文件 import 了 B 里的类型。
     *
     * <p>只统计项目内部依赖（以 rootPackage 开头），第三方依赖不参与架构分析。
     */
    public Map<String, Set<String>> packageDependencies() {
        Map<String, Set<String>> graph = new TreeMap<>();
        Map<String, String> typeToPackage = new LinkedHashMap<>();
        for (SourceFileInfo f : files) {
            if (!f.packageName().isBlank() && !f.typeName().isBlank()) {
                typeToPackage.put(f.packageName() + "." + f.typeName(), f.packageName());
            }
        }
        for (SourceFileInfo f : files) {
            Set<String> targets = graph.computeIfAbsent(f.packageName(), k -> new LinkedHashSet<>());
            for (String imp : f.projectImports(rootPackage)) {
                // import 可能指向嵌套类型，逐级回退匹配到已知包
                String target = resolvePackage(imp, typeToPackage);
                if (target != null && !target.equals(f.packageName())) {
                    targets.add(target);
                }
            }
        }
        return graph;
    }

    private static String resolvePackage(String importedType, Map<String, String> typeToPackage) {
        String candidate = importedType;
        while (candidate.contains(".")) {
            String pkg = typeToPackage.get(candidate);
            if (pkg != null) {
                return pkg;
            }
            candidate = candidate.substring(0, candidate.lastIndexOf('.'));
        }
        return null;
    }

    /** 体量最大的 N 个文件。 */
    public List<SourceFileInfo> largestFiles(int n) {
        return files.stream()
                .sorted(Comparator.comparingInt(SourceFileInfo::lineCount).reversed())
                .limit(n)
                .toList();
    }

    /** 方法最多的 N 个文件。 */
    public List<SourceFileInfo> mostMethods(int n) {
        return files.stream()
                .sorted(Comparator.comparingInt(SourceFileInfo::methods).reversed())
                .limit(n)
                .toList();
    }

    /** 是否为测试源（路径或类名含 test 约定）。 */
    public static boolean isTestFile(SourceFileInfo f) {
        String path = f.path().toLowerCase();
        String name = f.typeName().toLowerCase();
        return path.contains("/test/")
                || path.startsWith("src/test/")
                || name.endsWith("test")
                || name.endsWith("tests")
                || name.endsWith("it");
    }

    public long testFileCount() {
        return files.stream().filter(ProjectSnapshot::isTestFile).count();
    }
}
