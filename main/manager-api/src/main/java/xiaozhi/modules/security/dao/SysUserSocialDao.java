package xiaozhi.modules.security.dao;

import org.apache.ibatis.annotations.Mapper;

import xiaozhi.common.dao.BaseDao;
import xiaozhi.modules.security.entity.SysUserSocialEntity;

/**
 * 第三方社交登录关联表
 */
@Mapper
public interface SysUserSocialDao extends BaseDao<SysUserSocialEntity> {
}
