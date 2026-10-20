package dre4m1nd.devmentor.tools;

import io.agentscope.core.message.TextBlock;
import io.agentscope.core.message.ToolResultBlock;
import io.agentscope.core.message.ToolResultState;
import io.agentscope.core.tool.ToolResultConverter;
import java.lang.reflect.Type;

/**
 * 把工具返回的 {@link String} 原样包成成功的 {@link ToolResultBlock}。
 *
 * <p>默认转换器会把返回值 JSON 序列化，字符串因此被加上引号并转义换行，读起来很难受；
 * 教学类工具的输出都是人读的文本，用这个转换器更合适。
 */
public class PlainTextResultConverter implements ToolResultConverter {

    @Override
    public ToolResultBlock convert(Object result, Type returnType) {
        String text = result == null ? "(无输出)" : String.valueOf(result);
        return ToolResultBlock.of(TextBlock.builder().text(text).build())
                .withState(ToolResultState.SUCCESS);
    }
}
