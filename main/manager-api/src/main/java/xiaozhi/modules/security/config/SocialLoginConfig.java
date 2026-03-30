package xiaozhi.modules.security.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

import lombok.Data;

/**
 * 第三方社交登录 OAuth2 配置
 */
@Data
@Configuration
@ConfigurationProperties(prefix = "social-login")
public class SocialLoginConfig {

    private OAuthProvider google = new OAuthProvider();
    private OAuthProvider facebook = new OAuthProvider();
    private OAuthProvider github = new OAuthProvider();

    @Data
    public static class OAuthProvider {
        private String clientId = "";
        private String clientSecret = "";
        private String redirectUri = "";
    }
}
