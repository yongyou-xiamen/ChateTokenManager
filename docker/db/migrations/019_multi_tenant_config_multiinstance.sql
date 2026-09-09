-- 019: Phase 4 - 配置多实例
-- 1. router_settings 加 tenant_id (原本无单例约束, 直接加列)
-- 2. ai_policies_settings 加 tenant_id (需先删 CHECK id=1 约束)
-- 3. branding 加 tenant_id (需先删 CHECK id=1 约束)
-- 注: 这三张表的 id 列保持不变, tenant_id 作为普通列加唯一约束

-- 1. router_settings
ALTER TABLE aihelms.router_settings ADD COLUMN IF NOT EXISTS tenant_id BIGINT NOT NULL DEFAULT 1;
CREATE UNIQUE INDEX IF NOT EXISTS idx_router_settings_tenant ON aihelms.router_settings (tenant_id);

-- 2. ai_policies_settings
ALTER TABLE aihelms.ai_policies_settings DROP CONSTRAINT IF EXISTS ai_policies_settings_singleton;
ALTER TABLE aihelms.ai_policies_settings ADD COLUMN IF NOT EXISTS tenant_id BIGINT NOT NULL DEFAULT 1;
CREATE UNIQUE INDEX IF NOT EXISTS idx_ai_policies_settings_tenant ON aihelms.ai_policies_settings (tenant_id);

-- 3. branding
ALTER TABLE aihelms.branding DROP CONSTRAINT IF EXISTS branding_singleton;
ALTER TABLE aihelms.branding ADD COLUMN IF NOT EXISTS tenant_id BIGINT NOT NULL DEFAULT 1;
CREATE UNIQUE INDEX IF NOT EXISTS idx_branding_tenant ON aihelms.branding (tenant_id);
