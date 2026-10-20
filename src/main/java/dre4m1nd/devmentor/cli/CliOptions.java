package dre4m1nd.devmentor.cli;

import java.util.ArrayList;
import java.util.List;

/**
 * 命令行参数解析（不引入第三方 CLI 库）。
 *
 * <pre>
 *   --ask "..."        单轮提问后退出（非交互模式）
 *   --review [路径]    架构评审：静态分析指定项目并给出缺陷与改法，然后退出
 *   --scan-only        配合 --review：只打印静态分析事实，不调用模型
 *   --self-check       打印配置/工作区/工具清单后退出，不调用模型
 *   --model id         覆盖 devmentor.model-id
 *   --session id       覆盖会话 id
 *   --mode profile     覆盖权限档位
 *   --no-color         关闭颜色
 *   --verbose          工具输出全量
 *   --think            显示推理过程
 * </pre>
 */
public class CliOptions {

    private String ask;
    private String review;
    private boolean reviewRequested;
    private boolean scanOnly;
    private boolean selfCheck;
    private String model;
    private String session;
    private String mode;
    private boolean noColor;
    private boolean verbose;
    private boolean think;
    private final List<String> unknown = new ArrayList<>();

    public static CliOptions parse(String[] args) {
        CliOptions options = new CliOptions();
        if (args == null) {
            return options;
        }
        for (int i = 0; i < args.length; i++) {
            String arg = args[i];
            switch (arg) {
                case "--ask" -> options.ask = value(args, ++i, "--ask");
                case "--review" -> {
                    options.reviewRequested = true;
                    // 路径可选：下一个参数若不像 flag，就当作路径
                    if (i + 1 < args.length && args[i + 1] != null && !args[i + 1].startsWith("--")) {
                        options.review = args[++i];
                    }
                }
                case "--scan-only" -> options.scanOnly = true;
                case "--self-check", "--selfcheck" -> options.selfCheck = true;
                case "--model" -> options.model = value(args, ++i, "--model");
                case "--session" -> options.session = value(args, ++i, "--session");
                case "--mode" -> options.mode = value(args, ++i, "--mode");
                case "--no-color" -> options.noColor = true;
                case "--verbose" -> options.verbose = true;
                case "--think" -> options.think = true;
                default -> {
                    if (arg != null && !arg.startsWith("--") && options.ask == null) {
                        options.ask = arg;
                    } else {
                        options.unknown.add(arg);
                    }
                }
            }
        }
        return options;
    }

    private static String value(String[] args, int index, String flag) {
        if (index >= args.length) {
            throw new IllegalArgumentException(flag + " 需要一个参数值");
        }
        return args[index];
    }

    public String getAsk() {
        return ask;
    }

    /** 是否请求架构评审。 */
    public boolean isReview() {
        return reviewRequested;
    }

    /** 评审目标路径；为空表示用配置的代码目录。 */
    public String getReviewPath() {
        return review;
    }

    /** 只做静态分析，不调用模型。 */
    public boolean isScanOnly() {
        return scanOnly;
    }

    public boolean isSelfCheck() {
        return selfCheck;
    }

    public String getModel() {
        return model;
    }

    public String getSession() {
        return session;
    }

    public String getMode() {
        return mode;
    }

    public boolean isNoColor() {
        return noColor;
    }

    public boolean isVerbose() {
        return verbose;
    }

    public boolean isThink() {
        return think;
    }

    public List<String> getUnknown() {
        return unknown;
    }
}
