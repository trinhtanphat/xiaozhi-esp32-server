package xiaozhi.modules.security.dto;

import java.io.Serializable;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;

/**
 * 社交登录回调参数
 */
@Data
@Schema(description = "社交登录回调参数")
public class SocialCallbackDTO implements Serializable {

    @Schema(description = "OAuth授权码")
    @NotBlank(message = "授权码不能为空")
    private String code;

    @Schema(description = "状态码，防CSRF")
    private String state;
}
