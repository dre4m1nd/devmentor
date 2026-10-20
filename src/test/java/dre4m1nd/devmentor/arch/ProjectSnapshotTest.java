package dre4m1nd.devmentor.arch;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.List;
import org.junit.jupiter.api.Test;

class ProjectSnapshotTest {

    private static SourceFileInfo file(String pkg, String type, String... imports) {
        return new SourceFileInfo(
                "src/" + type + ".java",
                pkg,
                type,
                List.of(imports),
                50,
                5,
                3,
                2,
                20,
                5,
                false);
    }

    @Test
    void infersCommonRootPackage() {
        ProjectSnapshot s =
                new ProjectSnapshot(
                        List.of(
                                file("com.acme.shop.order", "Order"),
                                file("com.acme.shop.user", "User"),
                                file("com.acme.shop.pay", "Pay")));
        assertThat(s.rootPackage()).isEqualTo("com.acme.shop");
    }

    @Test
    void rootPackageEmptyWhenNothingInCommon() {
        ProjectSnapshot s =
                new ProjectSnapshot(List.of(file("com.a", "A"), file("org.b", "B")));
        assertThat(s.rootPackage()).isEmpty();
    }

    @Test
    void buildsPackageDependencyGraph() {
        ProjectSnapshot s =
                new ProjectSnapshot(
                        List.of(
                                file("com.acme.a", "A", "com.acme.b.B"),
                                file("com.acme.b", "B")));
        assertThat(s.packageDependencies().get("com.acme.a")).contains("com.acme.b");
        // 不产生自依赖
        assertThat(s.packageDependencies().get("com.acme.b")).isEmpty();
    }

    @Test
    void ignoresExternalImports() {
        ProjectSnapshot s =
                new ProjectSnapshot(
                        List.of(file("com.acme.a", "A", "java.util.List", "org.slf4j.Logger")));
        assertThat(s.packageDependencies().get("com.acme.a")).isEmpty();
    }

    @Test
    void aggregatesCounts() {
        ProjectSnapshot s =
                new ProjectSnapshot(
                        List.of(file("com.acme", "A"), file("com.acme", "B")));
        assertThat(s.fileCount()).isEqualTo(2);
        assertThat(s.totalLines()).isEqualTo(100);
        assertThat(s.totalMethods()).isEqualTo(10);
        assertThat(s.byPackage()).containsKey("com.acme");
    }

    @Test
    void identifiesTestFiles() {
        SourceFileInfo test =
                new SourceFileInfo("src/test/java/A.java", "com.acme", "ATest", List.of(), 10, 1, 0, 1, 5, 0, false);
        assertThat(ProjectSnapshot.isTestFile(test)).isTrue();
        SourceFileInfo prod = file("com.acme", "A");
        assertThat(ProjectSnapshot.isTestFile(prod)).isFalse();
    }
}
