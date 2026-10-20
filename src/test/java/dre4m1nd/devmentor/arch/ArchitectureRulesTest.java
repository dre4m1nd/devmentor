package dre4m1nd.devmentor.arch;

import static org.assertj.core.api.Assertions.assertThat;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class ArchitectureRulesTest {

    private static void write(Path root, String relative, String content) throws Exception {
        Path file = root.resolve(relative);
        Files.createDirectories(file.getParent());
        Files.writeString(file, content);
    }

    private static List<ArchFinding> findingsOf(Path dir) throws Exception {
        return ArchitectureAnalyzer.analyze(dir).findings();
    }

    @Test
    void detectsGodClass(@TempDir Path dir) throws Exception {
        StringBuilder sb = new StringBuilder("public class Huge {\n");
        for (int i = 0; i < 650; i++) {
            sb.append("    int f").append(i).append(";\n");
        }
        sb.append("}\n");
        write(dir, "com/acme/Huge.java", "package com.acme;\n" + sb);

        assertThat(findingsOf(dir))
                .anyMatch(f -> f.rule().equals("god-class") && f.severity() == ArchFinding.Severity.HIGH);
    }

    @Test
    void detectsLongMethod(@TempDir Path dir) throws Exception {
        StringBuilder body = new StringBuilder();
        for (int i = 0; i < 100; i++) {
            body.append("        int v").append(i).append(" = ").append(i).append(";\n");
        }
        write(dir, "com/acme/Long.java",
                "package com.acme;\npublic class Long {\n    void big() {\n" + body + "    }\n}\n");

        assertThat(findingsOf(dir)).anyMatch(f -> f.rule().equals("long-method"));
    }

    @Test
    void detectsPackageCycle(@TempDir Path dir) throws Exception {
        write(dir, "com/acme/a/A.java",
                "package com.acme.a;\nimport com.acme.b.B;\npublic class A { B b; }\n");
        write(dir, "com/acme/b/B.java",
                "package com.acme.b;\nimport com.acme.a.A;\npublic class B { A a; }\n");

        assertThat(findingsOf(dir))
                .anyMatch(f -> f.rule().equals("package-cycle") && f.severity() == ArchFinding.Severity.HIGH);
    }

    @Test
    void detectsLayerViolation(@TempDir Path dir) throws Exception {
        // repository 反向依赖 service
        write(dir, "com/acme/repository/Repo.java",
                "package com.acme.repository;\nimport com.acme.service.Svc;\npublic class Repo { Svc s; }\n");
        write(dir, "com/acme/service/Svc.java",
                "package com.acme.service;\npublic class Svc { }\n");

        assertThat(findingsOf(dir)).anyMatch(f -> f.rule().equals("layer-violation"));
    }

    @Test
    void detectsMissingTests(@TempDir Path dir) throws Exception {
        for (int i = 0; i < 12; i++) {
            write(dir, "com/acme/C" + i + ".java", "package com.acme;\npublic class C" + i + " { }\n");
        }
        assertThat(findingsOf(dir)).anyMatch(f -> f.rule().equals("no-tests"));
    }

    @Test
    void doesNotFlagNoTestsWhenTestsExist(@TempDir Path dir) throws Exception {
        for (int i = 0; i < 12; i++) {
            write(dir, "com/acme/C" + i + ".java", "package com.acme;\npublic class C" + i + " { }\n");
        }
        write(dir, "src/test/java/com/acme/C0Test.java",
                "package com.acme;\npublic class C0Test { }\n");
        assertThat(findingsOf(dir)).noneMatch(f -> f.rule().equals("no-tests"));
    }

    @Test
    void detectsFlatPackage(@TempDir Path dir) throws Exception {
        for (int i = 0; i < 22; i++) {
            write(dir, "com/acme/C" + i + ".java", "package com.acme;\npublic class C" + i + " { }\n");
        }
        assertThat(findingsOf(dir)).anyMatch(f -> f.rule().equals("flat-package"));
    }

    @Test
    void doesNotFlagPojoAsManyRoles(@TempDir Path dir) throws Exception {
        // 30 个一行 getter：方法数超阈值，但平均行数极短，纯 POJO 不是「职责过多」。
        StringBuilder sb = new StringBuilder("package com.acme;\npublic class Config {\n");
        for (int i = 0; i < 30; i++) {
            sb.append("    private int f").append(i).append(";\n");
        }
        for (int i = 0; i < 30; i++) {
            sb.append("    public int f").append(i).append("() { return this.f").append(i).append("; }\n");
        }
        sb.append("}\n");
        write(dir, "com/acme/Config.java", sb.toString());

        assertThat(findingsOf(dir)).noneMatch(f -> f.rule().equals("many-methods"));
    }

    @Test
    void stillFlagsFatClassWithManyMethods(@TempDir Path dir) throws Exception {
        StringBuilder sb = new StringBuilder("package com.acme;\npublic class Fat {\n");
        for (int i = 0; i < 30; i++) {
            sb.append("    int m").append(i).append("() {\n");
            for (int j = 0; j < 15; j++) {
                sb.append("        int v").append(j).append(" = ").append(j).append(";\n");
            }
            sb.append("        return 0;\n    }\n");
        }
        sb.append("}\n");
        write(dir, "com/acme/Fat.java", sb.toString());

        assertThat(findingsOf(dir)).anyMatch(f -> f.rule().equals("many-methods"));
    }

    @Test
    void detectsMixedPackageRoots(@TempDir Path dir) throws Exception {
        write(dir, "com/acme/A.java", "package com.acme;\npublic class A { }\n");
        write(dir, "org/other/B.java", "package org.other;\npublic class B { }\n");
        assertThat(findingsOf(dir)).anyMatch(f -> f.rule().equals("mixed-roots"));
    }

    @Test
    void cleanProjectHasNoHighSeverityFindings(@TempDir Path dir) throws Exception {
        write(dir, "com/acme/domain/Order.java",
                "package com.acme.domain;\npublic record Order(String id) { }\n");
        write(dir, "com/acme/service/OrderService.java",
                "package com.acme.service;\nimport com.acme.domain.Order;\n"
                        + "public class OrderService { public Order load() { return new Order(\"1\"); } }\n");
        write(dir, "com/acme/service/OrderServiceTest.java",
                "package com.acme.service;\npublic class OrderServiceTest { }\n");

        List<ArchFinding> findings = findingsOf(dir);
        assertThat(findings).noneMatch(f -> f.severity() == ArchFinding.Severity.HIGH);
    }

    @Test
    void cycleDetectionHandlesSelfLoops() {
        Map<String, Set<String>> graph = Map.of("a", Set.of("b"), "b", Set.of("a"));
        List<List<String>> cycles = ArchitectureRules.findCycles(graph, 10);
        assertThat(cycles).isNotEmpty();
        assertThat(cycles.get(0).get(0)).isEqualTo(cycles.get(0).get(cycles.get(0).size() - 1));
    }
}
