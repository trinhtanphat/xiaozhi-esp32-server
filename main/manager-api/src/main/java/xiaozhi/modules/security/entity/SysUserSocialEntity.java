package xiaozhi.modules.security.entity;

import java.util.Date;

import com.baomidou.mybatisplus.annotation.FieldFill;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableName;

import lombok.Data;
import lombok.EqualsAndHashCode;
import xiaozhi.common.entity.BaseEntity;

/**
 * 第三方社交登录关联表
 */
@Data
@EqualsAndHashCode(callSuper = false)
@TableName("sys_user_social")
public class SysUserSocialEntity extends BaseEntity {
    /**
     * 关联的系统用户ID
     */
    private Long userId;
    /**
     * OAuth提供商: google, facebook, github
     */
    private String provider;
    /**
     * 提供商用户唯一标识
     */
    private String providerUserId;
    /**
     * 提供商返回的邮箱
     */
    private String providerEmail;
    /**
     * 提供商返回的昵称
     */
    private String providerName;
    /**
     * 提供商返回的头像URL
     */
    private String providerAvatar;
    /**
     * 更新时间
     */
    @TableField(fill = FieldFill.INSERT_UPDATE)
    private Date updateDate;
}
