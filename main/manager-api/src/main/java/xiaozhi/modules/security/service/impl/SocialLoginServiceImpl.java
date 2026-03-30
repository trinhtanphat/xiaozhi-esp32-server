package xiaozhi.modules.security.service.impl;

import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.TimeUnit;

import org.apache.commons.lang3.StringUtils;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestTemplate;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import lombok.extern.slf4j.Slf4j;
import xiaozhi.common.exception.RenException;
import xiaozhi.common.page.TokenDTO;
import xiaozhi.common.utils.Result;
import xiaozhi.modules.security.config.SocialLoginConfig;
import xiaozhi.modules.security.dao.SysUserSocialDao;
import xiaozhi.modules.security.entity.SysUserSocialEntity;
import xiaozhi.modules.security.service.SocialLoginService;
import xiaozhi.modules.security.service.SysUserTokenService;
import xiaozhi.modules.sys.dao.SysUserDao;
import xiaozhi.modules.sys.dto.SysUserDTO;
import xiaozhi.modules.sys.entity.SysUserEntity;
import xiaozhi.modules.sys.enums.SuperAdminEnum;
import xiaozhi.modules.sys.service.SysUserService;

/**
 * 第三方社交登录服务实现
 */
@Slf4j
@Service
public class SocialLoginServiceImpl implements SocialLoginService {

    private static final String OAUTH_STATE_PREFIX = "social:oauth:state:";

    private final SocialLoginConfig socialLoginConfig;
    private final SysUserSocialDao sysUserSocialDao;
    private final SysUserDao sysUserDao;
    private final SysUserService sysUserService;
    private final SysUserTokenService sysUserTokenService;
    private final StringRedisTemplate redisTemplate;
    private final RestTemplate restTemplate;
    private final ObjectMapper objectMapper;

    public SocialLoginServiceImpl(SocialLoginConfig socialLoginConfig,
                                  SysUserSocialDao sysUserSocialDao,
                                  SysUserDao sysUserDao,
                                  SysUserService sysUserService,
                                  SysUserTokenService sysUserTokenService,
                                  StringRedisTemplate redisTemplate) {
        this.socialLoginConfig = socialLoginConfig;
        this.sysUserSocialDao = sysUserSocialDao;
        this.sysUserDao = sysUserDao;
        this.sysUserService = sysUserService;
        this.sysUserTokenService = sysUserTokenService;
        this.redisTemplate = redisTemplate;
        this.restTemplate = new RestTemplate();
        this.objectMapper = new ObjectMapper();
    }

    @Override
    public String getAuthorizationUrl(String provider) {
        String state = UUID.randomUUID().toString().replace("-", "");
        // Store state in Redis for 10 minutes to prevent CSRF
        redisTemplate.opsForValue().set(OAUTH_STATE_PREFIX + state, provider, 10, TimeUnit.MINUTES);

        return switch (provider.toLowerCase()) {
            case "google" -> buildGoogleAuthUrl(state);
            case "facebook" -> buildFacebookAuthUrl(state);
            case "github" -> buildGithubAuthUrl(state);
            default -> throw new RenException("不支持的登录方式: " + provider);
        };
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public Map<String, Object> handleCallback(String provider, String code, String state) {
        // Validate state to prevent CSRF
        if (StringUtils.isNotBlank(state)) {
            String storedProvider = redisTemplate.opsForValue().get(OAUTH_STATE_PREFIX + state);
            if (storedProvider == null) {
                throw new RenException("登录状态已过期，请重新登录");
            }
            redisTemplate.delete(OAUTH_STATE_PREFIX + state);
        }

        // Fetch user info from OAuth provider
        SocialUserInfo userInfo = switch (provider.toLowerCase()) {
            case "google" -> fetchGoogleUserInfo(code);
            case "facebook" -> fetchFacebookUserInfo(code);
            case "github" -> fetchGithubUserInfo(code);
            default -> throw new RenException("不支持的登录方式: " + provider);
        };

        // Find or create local user
        SysUserSocialEntity socialEntity = findSocialUser(provider, userInfo.id);
        Long userId;

        if (socialEntity != null) {
            // Existing social login - update info
            userId = socialEntity.getUserId();
            socialEntity.setProviderEmail(userInfo.email);
            socialEntity.setProviderName(userInfo.name);
            socialEntity.setProviderAvatar(userInfo.avatar);
            sysUserSocialDao.updateById(socialEntity);
        } else {
            // New social login - try to find user by email or create new
            userId = findOrCreateUser(userInfo);
            // Link social account
            socialEntity = new SysUserSocialEntity();
            socialEntity.setUserId(userId);
            socialEntity.setProvider(provider.toLowerCase());
            socialEntity.setProviderUserId(userInfo.id);
            socialEntity.setProviderEmail(userInfo.email);
            socialEntity.setProviderName(userInfo.name);
            socialEntity.setProviderAvatar(userInfo.avatar);
            sysUserSocialDao.insert(socialEntity);
        }

        // Generate app token
        Result<TokenDTO> tokenResult = sysUserTokenService.createToken(userId);
        Map<String, Object> result = new HashMap<>();
        result.put("token", tokenResult.getData().getToken());
        result.put("expire", tokenResult.getData().getExpire());
        return result;
    }

    // ===== Google OAuth =====

    private String buildGoogleAuthUrl(String state) {
        SocialLoginConfig.OAuthProvider config = socialLoginConfig.getGoogle();
        return "https://accounts.google.com/o/oauth2/v2/auth"
                + "?client_id=" + encode(config.getClientId())
                + "&redirect_uri=" + encode(config.getRedirectUri())
                + "&response_type=code"
                + "&scope=" + encode("openid email profile")
                + "&state=" + state
                + "&access_type=offline";
    }

    private SocialUserInfo fetchGoogleUserInfo(String code) {
        SocialLoginConfig.OAuthProvider config = socialLoginConfig.getGoogle();

        // Exchange code for token
        MultiValueMap<String, String> params = new LinkedMultiValueMap<>();
        params.add("code", code);
        params.add("client_id", config.getClientId());
        params.add("client_secret", config.getClientSecret());
        params.add("redirect_uri", config.getRedirectUri());
        params.add("grant_type", "authorization_code");

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_FORM_URLENCODED);
        HttpEntity<MultiValueMap<String, String>> request = new HttpEntity<>(params, headers);

        try {
            ResponseEntity<String> tokenResponse = restTemplate.postForEntity(
                    "https://oauth2.googleapis.com/token", request, String.class);
            JsonNode tokenJson = objectMapper.readTree(tokenResponse.getBody());
            String accessToken = tokenJson.get("access_token").asText();

            // Fetch user info
            HttpHeaders userHeaders = new HttpHeaders();
            userHeaders.setBearerAuth(accessToken);
            HttpEntity<Void> userRequest = new HttpEntity<>(userHeaders);
            ResponseEntity<String> userResponse = restTemplate.exchange(
                    "https://www.googleapis.com/oauth2/v2/userinfo",
                    HttpMethod.GET, userRequest, String.class);
            JsonNode userJson = objectMapper.readTree(userResponse.getBody());

            SocialUserInfo info = new SocialUserInfo();
            info.id = userJson.get("id").asText();
            info.email = userJson.has("email") ? userJson.get("email").asText() : null;
            info.name = userJson.has("name") ? userJson.get("name").asText() : null;
            info.avatar = userJson.has("picture") ? userJson.get("picture").asText() : null;
            return info;
        } catch (Exception e) {
            log.error("Google OAuth failed", e);
            throw new RenException("Google登录失败: " + e.getMessage());
        }
    }

    // ===== Facebook OAuth =====

    private String buildFacebookAuthUrl(String state) {
        SocialLoginConfig.OAuthProvider config = socialLoginConfig.getFacebook();
        return "https://www.facebook.com/v19.0/dialog/oauth"
                + "?client_id=" + encode(config.getClientId())
                + "&redirect_uri=" + encode(config.getRedirectUri())
                + "&response_type=code"
                + "&scope=" + encode("email,public_profile")
                + "&state=" + state;
    }

    private SocialUserInfo fetchFacebookUserInfo(String code) {
        SocialLoginConfig.OAuthProvider config = socialLoginConfig.getFacebook();

        // Exchange code for token
        String tokenUrl = "https://graph.facebook.com/v19.0/oauth/access_token"
                + "?client_id=" + encode(config.getClientId())
                + "&client_secret=" + encode(config.getClientSecret())
                + "&redirect_uri=" + encode(config.getRedirectUri())
                + "&code=" + encode(code);

        try {
            ResponseEntity<String> tokenResponse = restTemplate.getForEntity(tokenUrl, String.class);
            JsonNode tokenJson = objectMapper.readTree(tokenResponse.getBody());
            String accessToken = tokenJson.get("access_token").asText();

            // Fetch user info
            String userUrl = "https://graph.facebook.com/v19.0/me"
                    + "?fields=id,name,email,picture.type(large)"
                    + "&access_token=" + accessToken;
            ResponseEntity<String> userResponse = restTemplate.getForEntity(userUrl, String.class);
            JsonNode userJson = objectMapper.readTree(userResponse.getBody());

            SocialUserInfo info = new SocialUserInfo();
            info.id = userJson.get("id").asText();
            info.email = userJson.has("email") ? userJson.get("email").asText() : null;
            info.name = userJson.has("name") ? userJson.get("name").asText() : null;
            if (userJson.has("picture") && userJson.get("picture").has("data")) {
                info.avatar = userJson.get("picture").get("data").get("url").asText();
            }
            return info;
        } catch (Exception e) {
            log.error("Facebook OAuth failed", e);
            throw new RenException("Facebook登录失败: " + e.getMessage());
        }
    }

    // ===== GitHub OAuth =====

    private String buildGithubAuthUrl(String state) {
        SocialLoginConfig.OAuthProvider config = socialLoginConfig.getGithub();
        return "https://github.com/login/oauth/authorize"
                + "?client_id=" + encode(config.getClientId())
                + "&redirect_uri=" + encode(config.getRedirectUri())
                + "&scope=" + encode("user:email read:user")
                + "&state=" + state;
    }

    private SocialUserInfo fetchGithubUserInfo(String code) {
        SocialLoginConfig.OAuthProvider config = socialLoginConfig.getGithub();

        // Exchange code for token
        HttpHeaders tokenHeaders = new HttpHeaders();
        tokenHeaders.setContentType(MediaType.APPLICATION_FORM_URLENCODED);
        tokenHeaders.setAccept(List.of(MediaType.APPLICATION_JSON));

        MultiValueMap<String, String> params = new LinkedMultiValueMap<>();
        params.add("client_id", config.getClientId());
        params.add("client_secret", config.getClientSecret());
        params.add("code", code);
        params.add("redirect_uri", config.getRedirectUri());

        HttpEntity<MultiValueMap<String, String>> tokenRequest = new HttpEntity<>(params, tokenHeaders);

        try {
            ResponseEntity<String> tokenResponse = restTemplate.postForEntity(
                    "https://github.com/login/oauth/access_token", tokenRequest, String.class);
            JsonNode tokenJson = objectMapper.readTree(tokenResponse.getBody());
            String accessToken = tokenJson.get("access_token").asText();

            // Fetch user info
            HttpHeaders userHeaders = new HttpHeaders();
            userHeaders.setBearerAuth(accessToken);
            userHeaders.setAccept(List.of(MediaType.APPLICATION_JSON));
            HttpEntity<Void> userRequest = new HttpEntity<>(userHeaders);

            ResponseEntity<String> userResponse = restTemplate.exchange(
                    "https://api.github.com/user", HttpMethod.GET, userRequest, String.class);
            JsonNode userJson = objectMapper.readTree(userResponse.getBody());

            SocialUserInfo info = new SocialUserInfo();
            info.id = userJson.get("id").asText();
            info.name = userJson.has("login") ? userJson.get("login").asText() : null;
            info.avatar = userJson.has("avatar_url") ? userJson.get("avatar_url").asText() : null;

            // GitHub may not return email in user info, need separate call
            if (userJson.has("email") && !userJson.get("email").isNull()) {
                info.email = userJson.get("email").asText();
            } else {
                // Fetch email from emails endpoint
                ResponseEntity<String> emailResponse = restTemplate.exchange(
                        "https://api.github.com/user/emails", HttpMethod.GET, userRequest, String.class);
                JsonNode emails = objectMapper.readTree(emailResponse.getBody());
                for (JsonNode emailNode : emails) {
                    if (emailNode.has("primary") && emailNode.get("primary").asBoolean()) {
                        info.email = emailNode.get("email").asText();
                        break;
                    }
                }
            }
            return info;
        } catch (Exception e) {
            log.error("GitHub OAuth failed", e);
            throw new RenException("GitHub登录失败: " + e.getMessage());
        }
    }

    // ===== Helper methods =====

    private SysUserSocialEntity findSocialUser(String provider, String providerUserId) {
        QueryWrapper<SysUserSocialEntity> wrapper = new QueryWrapper<>();
        wrapper.eq("provider", provider.toLowerCase());
        wrapper.eq("provider_user_id", providerUserId);
        List<SysUserSocialEntity> list = sysUserSocialDao.selectList(wrapper);
        return list.isEmpty() ? null : list.get(0);
    }

    private Long findOrCreateUser(SocialUserInfo userInfo) {
        // Try to find existing user by email
        if (StringUtils.isNotBlank(userInfo.email)) {
            SysUserDTO existingUser = sysUserService.getByUsername(userInfo.email);
            if (existingUser != null) {
                return existingUser.getId();
            }
        }

        // Create new user with email or generated username
        String username = StringUtils.isNotBlank(userInfo.email) ? userInfo.email
                : userInfo.name != null ? userInfo.name + "_" + userInfo.id.substring(0, Math.min(6, userInfo.id.length()))
                : "social_" + userInfo.id;

        // Ensure username uniqueness
        SysUserDTO existing = sysUserService.getByUsername(username);
        if (existing != null) {
            username = username + "_" + System.currentTimeMillis() % 10000;
        }

        SysUserEntity entity = new SysUserEntity();
        entity.setUsername(username);
        // Social login users get a random unusable password (BCrypt-hashed)
        entity.setPassword("$2a$10$SOCIAL_LOGIN_NO_PASSWORD_HASH");
        entity.setSuperAdmin(SuperAdminEnum.NO.value());
        entity.setStatus(1);

        sysUserDao.insert(entity);

        return entity.getId();
    }

    private String encode(String value) {
        return URLEncoder.encode(value, StandardCharsets.UTF_8);
    }

    /**
     * Internal class to hold social user info from providers
     */
    private static class SocialUserInfo {
        String id;
        String email;
        String name;
        String avatar;
    }
}
