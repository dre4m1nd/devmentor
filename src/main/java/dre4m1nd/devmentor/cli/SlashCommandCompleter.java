package dre4m1nd.devmentor.cli;

import java.util.List;
import org.jline.reader.Candidate;
import org.jline.reader.Completer;
import org.jline.reader.LineReader;
import org.jline.reader.ParsedLine;

/**
 * 斜杠命令补全：补命令名时带右侧描述，补参数时只给固定取值。
 *
 * <p>行为对齐 Claude Code 的交互习惯：
 * <ul>
 *   <li>输入以 {@code /} 开头就给出全部命令，候选右侧显示一句话说明；
 *   <li>已经输入完整命令名后再打空格，补该命令的参数取值；
 *   <li>其它情况什么都不补，避免干扰正常提问。
 * </ul>
 *
 * <p>是否自动弹出菜单由 {@link LineReader#AUTO_MENU_LIST} 等变量控制，
 * 这里只负责「有哪些候选」。
 */
public class SlashCommandCompleter implements Completer {

    @Override
    public void complete(LineReader reader, ParsedLine line, List<Candidate> candidates) {
        if (line == null) {
            return;
        }
        String raw = line.line();
        if (raw == null) {
            return;
        }
        String trimmed = raw.stripLeading();
        if (!trimmed.startsWith("/")) {
            return;
        }

        int cursor = Math.min(line.cursor(), raw.length());
        String beforeCursor = raw.substring(0, cursor);

        // 判断光标是否已经越过命令名（即打了空格开始写参数）。
        // 注意："/mode " 带尾随空格时 DefaultParser 仍只切出一个词，
        // 所以只能用空格位置判断，不能依赖 words.size()。
        int space = beforeCursor.indexOf(' ');
        if (space >= 0) {
            String command = beforeCursor.substring(0, space).trim();
            if (command.length() <= 1) {
                return; // 只有 "/ "，没有命令名
            }
            String commandName = command.substring(1);
            String prefix = beforeCursor.substring(space + 1).trim();
            // 只补第一个参数；已经打了第二个空格就不再干预。
            if (prefix.indexOf(' ') >= 0) {
                return;
            }
            for (String value : SlashCommands.argumentCandidates(commandName)) {
                if (value.startsWith(prefix)) {
                    candidates.add(
                            new Candidate(
                                    value,
                                    value,
                                    null,
                                    SlashCommands.argumentDescription(commandName, value),
                                    null,
                                    null,
                                    true));
                }
            }
            return;
        }

        // 只在命令名这一段：补命令名。
        for (SlashCommands.Definition d : SlashCommands.DEFINITIONS) {
            if ("/exit".equals(d.name())) {
                continue; // 与 /quit 重复，菜单里只留一个
            }
            if (d.name().startsWith(beforeCursor)) {
                candidates.add(
                        new Candidate(
                                d.name(), d.name(), null, d.description(), null, null, true));
            }
        }
    }
}