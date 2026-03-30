-- Social login: create sys_user_social table for OAuth provider linkage
CREATE TABLE IF NOT EXISTS sys_user_social (
    id          BIGINT       NOT NULL,
    user_id     BIGINT       NOT NULL COMMENT '关联的系统用户ID',
    provider    VARCHAR(20)  NOT NULL COMMENT 'OAuth提供商: google, facebook, github',
    provider_user_id VARCHAR(255) NOT NULL COMMENT '提供商用户唯一标识',
    provider_email   VARCHAR(255) DEFAULT NULL COMMENT '提供商返回的邮箱',
    provider_name    VARCHAR(255) DEFAULT NULL COMMENT '提供商返回的昵称',
    provider_avatar  VARCHAR(512) DEFAULT NULL COMMENT '提供商返回的头像URL',
    create_date DATETIME     DEFAULT CURRENT_TIMESTAMP,
    update_date DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_provider_user (provider, provider_user_id),
    KEY idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='第三方社交登录关联表';
