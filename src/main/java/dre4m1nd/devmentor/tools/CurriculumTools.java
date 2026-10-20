package dre4m1nd.devmentor.tools;

import io.agentscope.core.tool.Tool;
import io.agentscope.core.tool.ToolParam;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.regex.Pattern;

/**
 * 读取工作区里的课程内容，让「按大纲教学」有真实依据，而不是模型自由发挥。
 */
public class CurriculumTools {

    private static final Pattern SLUG = Pattern.compile("^[a-z0-9][a-z0-9._-]*$");
    private static final int MAX_READ_CHARS = 6000;

    private final Path curriculumDir;

    public CurriculumTools(Path workspace) {
        this.curriculumDir = workspace.resolve("curriculum");
    }

    @Tool(
            name = "curriculum_list",
            readOnly = true,
            description =
                    "List the Java curriculum lessons available in the workspace, with slug and"
                        + " title. Call this before proposing a learning path or a lesson.")
    public String curriculumList() {
        List<Path> lessons = listLessons();
        if (lessons.isEmpty()) {
            return "课程目录为空（" + curriculumDir + "）。可以先用自由问答开始。";
        }
        StringBuilder sb = new StringBuilder("可用课程：\n");
        for (Path lesson : lessons) {
            String slug = slugOf(lesson);
            sb.append("- ").append(slug).append("  ").append(titleOf(lesson)).append('\n');
        }
        sb.append("\n用 curriculum_read 读取某一课的完整内容。");
        return sb.toString();
    }

    @Tool(
            name = "curriculum_read",
            readOnly = true,
            description = "Read one curriculum lesson by its slug (see curriculum_list).")
    public String curriculumRead(
            @ToolParam(name = "slug", description = "课程 slug，例如 03-collections-generics")
                    String slug) {
        if (slug == null || slug.isBlank()) {
            return "缺少参数 slug。先调用 curriculum_list 查看可用课程。";
        }
        String cleaned = slug.trim().toLowerCase(Locale.ROOT);
        if (cleaned.endsWith(".md")) {
            cleaned = cleaned.substring(0, cleaned.length() - 3);
        }
        if (!SLUG.matcher(cleaned).matches() || cleaned.contains("..")) {
            return "非法的课程名 \"" + slug + "\"：只允许字母、数字、点和连字符，且不能包含路径片段。";
        }
        Path file = curriculumDir.resolve(cleaned + ".md").normalize();
        if (!file.startsWith(curriculumDir.normalize())) {
            return "非法的课程名 \"" + slug + "\"。";
        }
        if (!Files.isRegularFile(file)) {
            List<Path> lessons = listLessons();
            StringBuilder sb = new StringBuilder("没有找到课程 \"" + cleaned + "\"。可用课程：\n");
            for (Path lesson : lessons) {
                sb.append("- ").append(slugOf(lesson)).append('\n');
            }
            return sb.toString();
        }
        try {
            String content = Files.readString(file, StandardCharsets.UTF_8);
            if (content.length() > MAX_READ_CHARS) {
                content = content.substring(0, MAX_READ_CHARS) + "\n…（内容已截断）";
            }
            return content;
        } catch (IOException e) {
            return "读取课程失败: " + e.getMessage();
        }
    }

    private List<Path> listLessons() {
        List<Path> lessons = new ArrayList<>();
        if (!Files.isDirectory(curriculumDir)) {
            return lessons;
        }
        try (var stream = Files.list(curriculumDir)) {
            stream.filter(Files::isRegularFile)
                    .filter(p -> p.getFileName().toString().toLowerCase(Locale.ROOT).endsWith(".md"))
                    .sorted()
                    .forEach(lessons::add);
        } catch (IOException ignored) {
            // 目录不可读时返回空列表
        }
        return lessons;
    }

    private static String slugOf(Path lesson) {
        String name = lesson.getFileName().toString();
        return name.substring(0, name.length() - 3);
    }

    private static String titleOf(Path lesson) {
        try {
            for (String line : Files.readAllLines(lesson, StandardCharsets.UTF_8)) {
                String trimmed = line.trim();
                if (trimmed.startsWith("#")) {
                    return trimmed.replaceFirst("^#+\\s*", "");
                }
            }
        } catch (IOException ignored) {
            // 读不到标题就用空串
        }
        return "";
    }
}
