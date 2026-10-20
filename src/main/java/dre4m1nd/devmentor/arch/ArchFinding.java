package dre4m1nd.devmentor.arch;

import java.util.List;

/**
 * 一条架构发现。由确定性规则产出（不是模型自由发挥），带证据与修改建议。
 *
 * @param rule 规则标识，便于引用
 * @param severity HIGH / MEDIUM / LOW
 * @param title 一句话问题描述
 * @param evidence 具体证据（文件:行、数字、依赖路径）
 * @param suggestion 修改意见
 * @param files 涉及的文件（相对路径）
 */
public record ArchFinding(
        String rule,
        Severity severity,
        String title,
        String evidence,
        String suggestion,
        List<String> files) {

    public enum Severity {
        HIGH("高"),
        MEDIUM("中"),
        LOW("低");

        private final String label;

        Severity(String label) {
            this.label = label;
        }

        public String label() {
            return label;
        }
    }

    /** 渲染成给模型看的一行（紧凑，避免 token 爆炸）。 */
    public String render() {
        return "["
                + severity.label()
                + "]["
                + rule
                + "] "
                + title
                + " | 证据: "
                + evidence
                + " | 建议: "
                + suggestion
                + (files.isEmpty() ? "" : " | 文件: " + String.join(", ", files));
    }
}
