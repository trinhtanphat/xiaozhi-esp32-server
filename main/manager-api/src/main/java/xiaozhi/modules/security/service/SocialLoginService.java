package xiaozhi.modules.security.service;

import java.util.Map;

/**
 * 第三方社交登录服务
 */
public interface SocialLoginService {

    /**
     * 获取OAuth授权URL
     *
     * @param provider 提供商: google, facebook, github
     * @return 授权URL
     */
    String getAuthorizationUrl(String provider);

    /**
     * 处理OAuth回调，返回用户token
     *
     * @param provider 提供商
     * @param code     授权码
     * @param state    状态码
     * @return 包含token等信息的Map
     */
    Map<String, Object> handleCallback(String provider, String code, String state);
}
