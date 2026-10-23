package dre4m1nd.devmentor.workspace;

import static org.assertj.core.api.Assertions.assertThat;

import io.agentscope.core.skill.AgentSkill;
import io.agentscope.core.skill.util.SkillUtil;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class WorkspaceBootstrapperTest {

    @Test
    void writesAllTemplatesOnFirstRun(@TempDir Path dir) {
        WorkspaceBootstrapper bootstrapper = new WorkspaceBootstrapper(dir);
        List<String> written = bootstrapper.ensure();

        assertThat(written).contains("AGENTS.md", "preferences.md");
        assertThat(dir.resolve("AGENTS.md")).exists();
        assertThat(dir.resolve("curriculum")).isDirectory();
        assertThat(dir.resolve("skills/java-code-review/SKILL.md")).exists();
    }

    @Test
    void doesNotOverwriteUserEdits(@TempDir Path dir) throws Exception {
        WorkspaceBootstrapper bootstrapper = new WorkspaceBootstrapper(dir);
        bootstrapper.ensure();

        Path agents = dir.resolve("AGENTS.md");
        Files.writeString(agents, "我的自定义人设", StandardCharsets.UTF_8);

        List<String> secondRun = bootstrapper.ensure();
        assertThat(secondRun).isEmpty();
        assertThat(Files.readString(agents, StandardCharsets.UTF_8)).isEqualTo("我的自定义人设");
    }

    @Test
    void skillsHaveParseableFrontMatter(@TempDir Path dir) throws Exception {
        new WorkspaceBootstrapper(dir).ensure();

        List<Path> skills;
        try (var stream = Files.walk(dir.resolve("skills"))) {
            skills = stream.filter(p -> p.getFileName().toString().equals("SKILL.md")).toList();
        }
        assertThat(skills).hasSizeGreaterThanOrEqualTo(3);

        for (Path skill : skills) {
            String md = Files.readString(skill, StandardCharsets.UTF_8);
            AgentSkill parsed = SkillUtil.createFrom(md, null, "test");
            assertThat(parsed.getName()).isNotBlank();
            assertThat(parsed.getDescription()).isNotBlank();
        }
    }

    @Test
    void everyCurriculumLessonHasTitleAndExercises(@TempDir Path dir) throws Exception {
        new WorkspaceBootstrapper(dir).ensure();

        try (var stream = Files.list(dir.resolve("curriculum"))) {
            List<Path> lessons = stream.filter(p -> p.toString().endsWith(".md")).sorted().toList();
            assertThat(lessons).hasSize(8);
            for (Path lesson : lessons) {
                String content = Files.readString(lesson, StandardCharsets.UTF_8);
                assertThat(content).as(lesson.getFileName().toString()).startsWith("# ");
                assertThat(content).as(lesson.getFileName().toString()).contains("练习");
            }
        }
    }
}
