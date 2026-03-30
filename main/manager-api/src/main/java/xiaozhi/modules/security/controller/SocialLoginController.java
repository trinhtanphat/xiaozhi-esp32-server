package xiaozhi.modules.security.controller;

import java.util.HashMap;
import java.util.Map;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.AllArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import xiaozhi.common.utils.Result;
import xiaozhi.modules.security.dto.SocialCallbackDTO;
import xiaozhi.modules.security.service.SocialLoginService;

/**
 * 第三方社交登录控制层
 */
@Slf4j
@AllArgsConstructor
@RestController
@RequestMapping("/user/social-login")
@Tag(name = "第三方社交登录")
public class SocialLoginController {

    private final SocialLoginService socialLoginService;

    @GetMapping("/{provider}/url")
    @Operation(summary = "获取OAuth授权URL")
    public Result<Map<String, String>> getAuthUrl(@PathVariable String provider) {
        String url = socialLoginService.getAuthorizationUrl(provider);
        Map<String, String> data = new HashMap<>();
        data.put("url", url);
        Result<Map<String, String>> result = new Result<>();
        result.setData(data);
        return result;
    }

    @PostMapping("/{provider}/callback")
    @Operation(summary = "OAuth回调处理")
    public Result<Map<String, Object>> callback(@PathVariable String provider,
                                                 @RequestBody SocialCallbackDTO dto) {
        Map<String, Object> tokenData = socialLoginService.handleCallback(provider, dto.getCode(), dto.getState());
        Result<Map<String, Object>> result = new Result<>();
        result.setData(tokenData);
        return result;
    }
}
