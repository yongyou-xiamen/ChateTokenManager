-- 017: 多租户基础设施
-- 1. 创建 tenants 表
-- 2. 默认租户 (id=1, 承载现有数据)
-- 3. users 加 tenant_id + is_tenant_admin
-- 4. admin_audit_logs 加 tenant_id
-- 5. roles 加 tenant_id (系统角色 NULL 全局共享)
-- 6. 索引
-- 注: 业务表(departments/projects/ai_keys 等)的 tenant_id 留到 Phase 2 迁移
-- 注: branding/router_settings/ai_policies_settings 单例改多实例留到 Phase 4 迁移

-- 1. tenants 表
CREATE TABLE IF NOT EXISTS aihelms.tenants (
    id BIGINT PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    settings JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. 默认租户
INSERT INTO aihelms.tenants (id, name, slug, status)
VALUES (1, 'Default', 'default', 'active')
ON CONFLICT (id) DO NOTHING;

-- 3. users 加 tenant_id + is_tenant_admin
ALTER TABLE aihelms.users ADD COLUMN IF NOT EXISTS tenant_id BIGINT NOT NULL DEFAULT 1;
ALTER TABLE aihelms.users ADD COLUMN IF NOT EXISTS is_tenant_admin BOOLEAN NOT NULL DEFAULT FALSE;

-- 现有 is_admin=True 且非超管的用户提升为租户管理员
UPDATE aihelms.users
SET is_tenant_admin = TRUE
WHERE is_admin = TRUE AND is_super_admin = FALSE;

-- 超管也标记为租户管理员(归默认租户)
UPDATE aihelms.users
SET is_tenant_admin = TRUE
WHERE is_super_admin = TRUE;

-- FK 约束(幂等: 先删再加)
ALTER TABLE aihelms.users DROP CONSTRAINT IF EXISTS fk_users_tenant;
ALTER TABLE aihelms.users ADD CONSTRAINT fk_users_tenant
    FOREIGN KEY (tenant_id) REFERENCES aihelms.tenants(id);

-- 4. admin_audit_logs 加 tenant_id (nullable, 历史日志无 tenant)
ALTER TABLE aihelms.admin_audit_logs ADD COLUMN IF NOT EXISTS tenant_id BIGINT;

-- 5. roles 加 tenant_id (nullable: 系统角色 NULL 全局共享, 自定义角色按租户)
ALTER TABLE aihelms.roles ADD COLUMN IF NOT EXISTS tenant_id BIGINT;

-- 6. 索引(加速 tenant 过滤)
CREATE INDEX IF NOT EXISTS idx_users_tenant ON aihelms.users (tenant_id);
CREATE INDEX IF NOT EXISTS idx_roles_tenant ON aihelms.roles (tenant_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_tenant ON aihelms.admin_audit_logs (tenant_id);
