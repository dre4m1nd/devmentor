package dre4m1nd.devmentor.tools;

import io.agentscope.core.tool.Tool;
import io.agentscope.core.tool.ToolParam;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.List;

/**
 * 学习进度：追加写入工作区的 {@code progress.md}，让导师跨会话记得你学到哪了。
 */
public class ProgressTools {

    private static final DateTimeFormatter STAMP = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm");

    private final Path progressFile;

    public ProgressTools(Path workspace) {
        this.progressFile = workspace.resolve("progress.md");
    }

    @Tool(
            name = "progress_read",
            readOnly = true,
            description = "Read the learner's recorded progress (progress.md) from the workspace.")
    public String progressRead() {
        if (!Files.isRegularFile(progressFile)) {
            return "还没有学习记录。可以用 progress_record 记录第一个知识点。";
        }
        try {
            String content = Files.readString(progressFile, StandardCharsets.UTF_8).strip();
            return content.isEmpty() ? "学习记录还是空的。" : content;
        } catch (IOException e) {
            return "读取学习记录失败: " + e.getMessage();
        }
    }

    @Tool(
            name = "progress_record",
            readOnly = false,
            description =
                    "Append one learning-progress entry (topic, status, optional note) to"
                        + " progress.md. Use it after the learner finishes or struggles with a"
                        + " topic so future sessions can pick up where you left off.")
    public String progressRecord(
            @ToolParam(name = "topic", description = "知识点或课程，例如「泛型通配符」") String topic,
            @ToolParam(name = "status", description = "状态：学习中 / 已掌握 / 待复习") String status,
            @ToolParam(name = "note", description = "可选的补充说明", required = false) String note) {
        if (topic == null || topic.isBlank()) {
            return "缺少参数 topic。";
        }
        String state = status == null || status.isBlank() ? "学习中" : status.trim();
        String line =
                "- "
                        + LocalDateTime.now().format(STAMP)
                        + " | "
                        + topic.trim()
                        + " | "
                        + state
                        + (note == null || note.isBlank() ? "" : " | " + note.trim())
                        + System.lineSeparator();
        try {
            if (progressFile.getParent() != null) {
                Files.createDirectories(progressFile.getParent());
            }
            boolean fresh = !Files.exists(progressFile);
            if (fresh) {
                Files.writeString(
                        progressFile,
                        "# 学习进度" + System.lineSeparator() + System.lineSeparator(),
                        StandardCharsets.UTF_8,
                        StandardOpenOption.CREATE);
            }
            Files.writeString(
                    progressFile, line, StandardCharsets.UTF_8, StandardOpenOption.APPEND);
            return "已记录：" + line.strip();
        } catch (IOException e) {
            return "写入学习记录失败: " + e.getMessage();
        }
    }

    /** 供测试与 CLI 展示使用。 */
    public Path getProgressFile() {
        return progressFile;
    }

    /** 当前记录条数（不含表头）。 */
    public int entryCount() {
        if (!Files.isRegularFile(progressFile)) {
            return 0;
        }
        try {
            List<String> lines = Files.readAllLines(progressFile, StandardCharsets.UTF_8);
            return (int) lines.stream().filter(l -> l.startsWith("- ")).count();
        } catch (IOException e) {
            return 0;
        }
    }
}
