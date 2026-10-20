package dre4m1nd.devmentor.config;

/** 配置不完整时抛出的异常，消息面向最终用户，可直接打印。 */
public class DevMentorConfigException extends RuntimeException {

    public DevMentorConfigException(String message) {
        super(message);
    }

    public DevMentorConfigException(String message, Throwable cause) {
        super(message, cause);
    }
}
