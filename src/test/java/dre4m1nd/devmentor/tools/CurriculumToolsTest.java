package dre4m1nd.devmentor.tools;

import static org.assertj.core.api.Assertions.assertThat;

import dre4m1nd.devmentor.workspace.WorkspaceBootstrapper;
import java.nio.file.Path;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class CurriculumToolsTest {

    @Test
    void listsBundledLessons(@TempDir Path dir) {
        new WorkspaceBootstrapper(dir).ensure();
        String list = new CurriculumTools(dir).curriculumList();
        assertThat(list).contains("01-syntax-and-types").contains("08-testing-and-spring");
    }

    @Test
    void readsOneLesson(@TempDir Path dir) {
        new WorkspaceBootstrapper(dir).ensure();
        String content = new CurriculumTools(dir).curriculumRead("03-collections-generics");
        assertThat(content).contains("集合与泛型");
    }

    @Test
    void rejectsPathTraversal(@TempDir Path dir) {
        new WorkspaceBootstrapper(dir).ensure();
        CurriculumTools tools = new CurriculumTools(dir);
        assertThat(tools.curriculumRead("../AGENTS")).contains("非法");
        assertThat(tools.curriculumRead("..%2fAGENTS")).contains("非法");
        assertThat(tools.curriculumRead("/etc/passwd")).contains("非法");
    }

    @Test
    void unknownLessonSuggestsAlternatives(@TempDir Path dir) {
        new WorkspaceBootstrapper(dir).ensure();
        String result = new CurriculumTools(dir).curriculumRead("99-nope");
        assertThat(result).contains("没有找到").contains("01-syntax-and-types");
    }
}
