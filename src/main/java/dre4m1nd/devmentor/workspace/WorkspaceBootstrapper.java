package dre4m1nd.devmentor.workspace;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.List;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Component;

/**
 * 首次运行时把 classpath 里的导师工作区模板落盘。
 *
 * <p>规则是「不存在才写」：已经存在的文件一律不覆盖，这样用户对手写的人设、课程、偏好做的
 * 修改不会被升级冲掉。资源清单是显式列出的，避免在 jar 内做目录扫描。
 */
@Component
public class WorkspaceBootstrapper {

    private static final Logger log = LoggerFactory.getLogger(WorkspaceBootstrapper.class);

    static final String TEMPLATE_ROOT = "devmentor/workspace/";

    /** 需要落盘的模板文件（相对路径）。 */
    static final List<String> TEMPLATES =
            List.of(
                    "AGENTS.md",
                    "preferences.md",
                    "curriculum/01-syntax-and-types.md",
                    "curriculum/02-oop-and-design.md",
                    "curriculum/03-collections-generics.md",
                    "curriculum/04-streams-lambda.md",
                    "curriculum/05-exceptions-io.md",
                    "curriculum/06-concurrency.md",
                    "curriculum/07-jvm-and-gc.md",
                    "curriculum/08-testing-and-spring.md",
                    "skills/java-code-review/SKILL.md",
                    "skills/java-debug-coach/SKILL.md",
                    "skills/java-exercise-designer/SKILL.md",
                    "skills/java-architecture-review/SKILL.md");

    private final Path workspace;

    public WorkspaceBootstrapper(Path workspace) {
        this.workspace = workspace;
    }

    /**
     * 落盘所有缺失的模板文件。
     *
     * @return 本次实际写入的相对路径列表（已存在的不会出现在结果里）
     */
    public List<String> ensure() {
        List<String> written = new ArrayList<>();
        for (String relative : TEMPLATES) {
            Path target = workspace.resolve(relative);
            if (Files.exists(target)) {
                continue;
            }
            ClassPathResource resource = new ClassPathResource(TEMPLATE_ROOT + relative);
            if (!resource.exists()) {
                log.warn("工作区模板缺失: {}", TEMPLATE_ROOT + relative);
                continue;
            }
            try {
                if (target.getParent() != null) {
                    Files.createDirectories(target.getParent());
                }
                try (InputStream in = resource.getInputStream()) {
                    Files.copy(in, target, StandardCopyOption.REPLACE_EXISTING);
                }
                written.add(relative);
            } catch (IOException e) {
                log.warn("写入工作区文件失败 {}: {}", relative, e.getMessage());
            }
        }
        if (!written.isEmpty()) {
            log.info("工作区已初始化，写入 {} 个文件到 {}", written.size(), workspace);
        }
        return written;
    }

    /** 读取工作区文件内容；不存在时返回空串。 */
    public static String readIfPresent(Path file) {
        if (!Files.isRegularFile(file)) {
            return "";
        }
        try {
            return Files.readString(file, StandardCharsets.UTF_8);
        } catch (IOException e) {
            return "";
        }
    }

    public Path getWorkspace() {
        return workspace;
    }
}
