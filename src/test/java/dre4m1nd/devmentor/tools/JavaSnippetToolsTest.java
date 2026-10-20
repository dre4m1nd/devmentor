package dre4m1nd.devmentor.tools;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

class JavaSnippetToolsTest {

    private final JavaSnippetTools tools = new JavaSnippetTools(5, 2000);

    @Test
    void runsHelloWorld() {
        String source =
                """
                public class Snippet {
                    public static void main(String[] args) {
                        System.out.println("Hello, DevMentor");
                    }
                }
                """;
        String result = tools.javaRunSnippet(source, null);
        assertThat(result).contains("退出码: 0").contains("Hello, DevMentor");
    }

    @Test
    void feedsStdin() {
        String source =
                """
                import java.util.Scanner;
                public class Snippet {
                    public static void main(String[] args) {
                        var scanner = new Scanner(System.in);
                        System.out.println("收到:" + scanner.nextLine());
                    }
                }
                """;
        String result = tools.javaRunSnippet(source, "42");
        assertThat(result).contains("收到:42");
    }

    @Test
    void reportsCompileErrorWithLineNumber() {
        String source =
                """
                public class Snippet {
                    public static void main(String[] args) {
                        int x = "not an int";
                    }
                }
                """;
        String result = tools.javaRunSnippet(source, null);
        assertThat(result).contains("编译失败").contains("第 3 行");
    }

    @Test
    void compileCheckSucceedsForValidSource() {
        String result = tools.javaCompileCheck("public class Snippet { int add(int a,int b){return a+b;} }");
        assertThat(result).contains("编译通过");
    }

    @Test
    void killsInfiniteLoop() {
        String source =
                """
                public class Snippet {
                    public static void main(String[] args) {
                        while (true) { }
                    }
                }
                """;
        JavaSnippetTools fast = new JavaSnippetTools(1, 2000);
        String result = fast.javaRunSnippet(source, null);
        assertThat(result).contains("超时");
    }

    @Test
    void rejectsOversizedSource() {
        String huge = "a".repeat(5000);
        String result = tools.javaRunSnippet(huge, null);
        assertThat(result).contains("源码过长");
    }

    @Test
    void runsPublicClassWithMatchingFileName() {
        String source =
                """
                public class HelloDevMentor {
                    public static void main(String[] args) {
                        System.out.println("Hello DevMentor");
                    }
                }
                """;
        String result = tools.javaRunSnippet(source, null);
        assertThat(result).contains("退出码: 0").contains("Hello DevMentor");
        assertThat(result).doesNotContain("应在名为");
    }

    @Test
    void derivesFileNameFromDeclaredType() {
        assertThat(JavaSnippetTools.fileNameFor("public class Foo {}")).isEqualTo("Foo.java");
        assertThat(JavaSnippetTools.fileNameFor("public record Point(int x, int y) {}"))
                .isEqualTo("Point.java");
        assertThat(JavaSnippetTools.fileNameFor("class Bar {}")).isEqualTo("Bar.java");
        assertThat(JavaSnippetTools.fileNameFor("public interface Baz {}")).isEqualTo("Baz.java");
        assertThat(JavaSnippetTools.fileNameFor("System.out.println(1);")).isEqualTo("Snippet.java");
    }

    @Test
    void rejectsBlankSource() {
        assertThat(tools.javaRunSnippet("  ", null)).contains("源码为空");
        assertThat(tools.javaCompileCheck(null)).contains("源码为空");
    }
}
