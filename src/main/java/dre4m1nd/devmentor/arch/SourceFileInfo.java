package dre4m1nd.devmentor.arch;

/**
 * 一个源文件的静态分析结果（不含任何 LLM 判断，纯事实）。
 *
 * @param path 相对项目根的路径
 * @param packageName 包名，默认包为空串
 * @param typeName 顶层类型名
 * @param imports import 全限定名列表
 * @param lineCount 行数
 * @param methods 方法数
 * @param fields 字段数
 * @param publicMethods public 方法数
 * @param maxMethodLines 最长方法的行数
 * @param commentLines 注释行数
 * @param hasJavadoc 是否有 Javadoc
 */
public record SourceFileInfo(
        String path,
        String packageName,
        String typeName,
        java.util.List<String> imports,
        int lineCount,
        int methods,
        int fields,
        int publicMethods,
        int maxMethodLines,
        int commentLines,
        boolean hasJavadoc) {

    /** 该文件依赖的其它「项目内」类型（按包前缀推断）。 */
    public java.util.List<String> projectImports(String rootPackage) {
        if (rootPackage == null || rootPackage.isBlank()) {
            return java.util.List.of();
        }
        return imports.stream().filter(i -> i.startsWith(rootPackage + ".")).toList();
    }
}
