package dre4m1nd.devmentor.tools;

import static org.assertj.core.api.Assertions.assertThat;

import java.nio.file.Files;
import java.nio.file.Path;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class ArchitectureToolsTest {

    @TempDir Path project;
    private ArchitectureTools tools;

    @BeforeEach
    void setUp() throws Exception {
        Path service = project.resolve("src/main/java/com/acme/service");
        Files.createDirectories(service);
        Files.writeString(service.resolve("OrderService.java"),
                """
                package com.acme.service;

                import com.acme.repository.OrderRepository;

                public class OrderService {
                    private final OrderRepository repo;
                    public OrderService(OrderRepository repo) { this.repo = repo; }
                    public int count() { return repo.all().size(); }
                }
                """);
        Path repo = project.resolve("src/main/java/com/acme/repository");
        Files.createDirectories(repo);
        Files.writeString(repo.resolve("OrderRepository.java"),
                """
                package com.acme.repository;

                import com.acme.service.OrderService;

                public class OrderRepository {
                    OrderService service;
                    public java.util.List<String> all() { return java.util.List.of(); }
                }
                """);
        tools = new ArchitectureTools(project, project.resolve(".reports"));
    }

    @Test
    void scanReturnsFactsAndWritesReport() {
        String out = tools.archScan(null, null);
        assertThat(out).contains("项目架构事实").contains("com.acme");
        assertThat(out).contains("包级依赖");
        assertThat(project.resolve(".reports/architecture-report.md")).exists();
    }

    @Test
    void scanReportsCycleBetweenServiceAndRepository() {
        String out = tools.archScan(null, null);
        assertThat(out).contains("package-cycle");
    }

    @Test
    void findingsFiltersBySeverity() {
        String high = tools.archFindings("HIGH");
        assertThat(high).contains("package-cycle");
        assertThat(high).doesNotContain("no-comments");
    }

    @Test
    void dependenciesShowsGraph() {
        String out = tools.archDependencies(null);
        assertThat(out).contains("com.acme.service").contains("com.acme.repository");
        assertThat(out).contains("循环依赖");
    }

    @Test
    void fileProfileWorksForKnownFile() {
        String out = tools.archFileProfile("src/main/java/com/acme/service/OrderService.java");
        assertThat(out).contains("OrderService").contains("行数").contains("方法数");
    }

    @Test
    void fileProfileRejectsTraversal() {
        assertThat(tools.archFileProfile("../../etc/passwd")).contains("非法");
    }

    @Test
    void readSourceShowsLineNumbers() {
        String out = tools.archReadSource("src/main/java/com/acme/service/OrderService.java", 1, 3);
        assertThat(out).contains("    1 |").contains("package com.acme.service");
    }

    @Test
    void readSourceRejectsTraversal() {
        assertThat(tools.archReadSource("../outside.java", null, null)).contains("非法");
        assertThat(tools.archReadSource("/etc/passwd", null, null)).contains("非法");
    }

    @Test
    void scanOnMissingDirectoryIsReported() {
        assertThat(tools.archScan("D:/definitely/not/here", null)).contains("不存在");
    }
}
