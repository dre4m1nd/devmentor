package dre4m1nd.devmentor.tools;

import static org.assertj.core.api.Assertions.assertThat;

import java.nio.file.Path;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class ProgressToolsTest {

    @Test
    void recordsAndReadsBack(@TempDir Path dir) {
        ProgressTools tools = new ProgressTools(dir);
        assertThat(tools.progressRead()).contains("还没有学习记录");

        tools.progressRecord("泛型通配符", "学习中", "PECS 还不太熟");
        tools.progressRecord("Stream 分组", "已掌握", null);

        String content = tools.progressRead();
        assertThat(content).contains("泛型通配符").contains("PECS").contains("Stream 分组");
        assertThat(tools.entryCount()).isEqualTo(2);
    }

    @Test
    void rejectsMissingTopic(@TempDir Path dir) {
        assertThat(new ProgressTools(dir).progressRecord(null, "学习中", null)).contains("缺少参数");
    }
}
