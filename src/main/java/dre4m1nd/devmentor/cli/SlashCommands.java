package dre4m1nd.devmentor.cli;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/**
 * 斜杠命令的解析与元数据（名称、说明、补全候选）。
 */
public final class SlashCommands {

    /** 一条命令的定义。 */
    public record Definition(String name, String usage, String description) {}

    public static final List<Definition> DEFINITIONS =
            List.of(
                    new Definition("/help", "/help", "显示帮助"),
                    new Definition("/new", "/new [名字]", "开启新会话"),
                    new Definition("/reset", "/reset", "清空当前会话上下文"),
                    new Definition("/mode", "/mode <interactive|read-only|full>", "切换权限档位"),
                    new Definition("/plan", "/plan [on|off]", "切换 plan 模式"),
                    new Definition("/arch", "/arch [路径]", "架构评审：静态分析当前项目"),
                    new Definition("/lesson", "/lesson [slug]", "列出或阅读课程"),
                    new Definition("/progress", "/progress", "查看学习进度"),
                    new Definition("/lang", "/lang <zh|en>", "切换讲解语言"),
                    new Definition("/model", "/model [id]", "查看或切换模型"),
                    new Definition("/tools", "/tools", "列出可用工具"),
                    new Definition("/workspace", "/workspace", "显示工作区与代码目录"),
                    new Definition("/session", "/session", "显示当前会话信息"),
                    new Definition("/verbose", "/verbose", "切换工具输出全量/摘要"),
                    new Definition("/think", "/think", "切换是否显示推理过程"),
                    new Definition("/quit", "/quit", "退出"),
                    new Definition("/exit", "/exit", "退出"));

    private SlashCommands() {}

    /** 判断输入是否为斜杠命令。 */
    public static boolean isCommand(String line) {
        return line != null && line.startsWith("/");
    }

    /** 解析结果：命令名（不含斜杠、小写）与参数列表。 */
    public record Parsed(String name, List<String> args) {

        public String arg(int index) {
            return index < args.size() ? args.get(index) : null;
        }
    }

    /** 解析一行命令；非法输入返回 {@code null}。允许命令前有空白。 */
    public static Parsed parse(String line) {
        if (line == null) {
            return null;
        }
        String trimmed = line.trim();
        if (!trimmed.startsWith("/")) {
            return null;
        }
        String[] parts = trimmed.substring(1).split("\\s+");
        if (parts.length == 0 || parts[0].isEmpty()) {
            return null;
        }
        List<String> args = new ArrayList<>();
        for (int i = 1; i < parts.length; i++) {
            if (!parts[i].isEmpty()) {
                args.add(parts[i]);
            }
        }
        return new Parsed(parts[0].toLowerCase(Locale.ROOT), List.copyOf(args));
    }

    /** 命令名是否已知。 */
    public static boolean isKnown(String name) {
        return DEFINITIONS.stream().anyMatch(d -> d.name().substring(1).equals(name));
    }

    /** 帮助文本。 */
    public static String helpText() {
        StringBuilder sb = new StringBuilder("可用命令：\n");
        for (Definition d : DEFINITIONS) {
            if ("/exit".equals(d.name())) {
                continue;
            }
            sb.append(String.format("  %-38s %s%n", d.usage(), d.description()));
        }
        sb.append("\n直接输入内容即与导师对话；Ctrl+C 中断当前回答，Ctrl+D 退出。");
        return sb.toString();
    }

    /** 补全候选：所有命令名。 */
    public static List<String> commandNames() {
        return DEFINITIONS.stream().map(Definition::name).distinct().toList();
    }
}
