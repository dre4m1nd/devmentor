package dre4m1nd.devmentor.arch;

import static org.assertj.core.api.Assertions.assertThat;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Set;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class JavaSourceScannerTest {

    private static void write(Path root, String relative, String content) throws Exception {
        Path file = root.resolve(relative);
        Files.createDirectories(file.getParent());
        Files.writeString(file, content);
    }

    @Test
    void extractsPackageTypeAndCounts(@TempDir Path dir) throws Exception {
        write(dir, "src/main/java/com/acme/Order.java",
                """
                package com.acme;

                import java.util.List;
                import com.acme.util.Helper;

                public class Order {
                    private int id;
                    private String name;

                    public void a() { }
                    void b() { }
                    private int c() { return 1; }
                }
                """);

        List<SourceFileInfo> files = JavaSourceScanner.scan(dir, Set.of("target"), 100);
        assertThat(files).hasSize(1);
        SourceFileInfo f = files.get(0);
        assertThat(f.packageName()).isEqualTo("com.acme");
        assertThat(f.typeName()).isEqualTo("Order");
        assertThat(f.imports()).contains("java.util.List", "com.acme.util.Helper");
        assertThat(f.methods()).isEqualTo(3);
        assertThat(f.publicMethods()).isEqualTo(1);
        assertThat(f.fields()).isGreaterThanOrEqualTo(2);
    }

    @Test
    void skipsExcludedAndHiddenDirs(@TempDir Path dir) throws Exception {
        write(dir, "src/A.java", "public class A { }");
        write(dir, "target/B.java", "public class B { }");
        write(dir, ".idea/C.java", "public class C { }");

        List<SourceFileInfo> files = JavaSourceScanner.scan(dir, Set.of("target"), 100);
        assertThat(files).extracting(SourceFileInfo::typeName).containsExactly("A");
    }

    @Test
    void reportsLongestMethod(@TempDir Path dir) throws Exception {
        StringBuilder body = new StringBuilder();
        for (int i = 0; i < 40; i++) {
            body.append("        int v").append(i).append(" = ").append(i).append(";\n");
        }
        write(dir, "Long.java",
                "public class Long {\n    void big() {\n" + body + "    }\n}\n");

        SourceFileInfo f = JavaSourceScanner.scan(dir, Set.of(), 10).get(0);
        assertThat(f.maxMethodLines()).isGreaterThan(40);
    }

    @Test
    void countsCommentLines(@TempDir Path dir) throws Exception {
        write(dir, "Doc.java",
                """
                /** 类的说明。 */
                public class Doc {
                    // 单行注释
                    void m() { }
                }
                """);
        SourceFileInfo f = JavaSourceScanner.scan(dir, Set.of(), 10).get(0);
        assertThat(f.commentLines()).isGreaterThanOrEqualTo(2);
        assertThat(f.hasJavadoc()).isTrue();
    }

    @Test
    void ignoresUnparseableFile(@TempDir Path dir) throws Exception {
        write(dir, "Good.java", "public class Good { }");
        write(dir, "Bad.java", "public class { this is not java");
        List<SourceFileInfo> files = JavaSourceScanner.scan(dir, Set.of(), 10);
        assertThat(files).extracting(SourceFileInfo::typeName).contains("Good");
    }
}
