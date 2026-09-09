-- 020: ai_policies_audits 加 tenant_id 隔离
-- 审查任务历史无 tenant_id, 用默认租户 1 回填, 新审查任务由 service 写入 tenant_id

ALTER TABLE aihelms.ai_policies_audits
    ADD COLUMN IF NOT EXISTS tenant_id BIGINT NOT NULL DEFAULT 1;
CREATE INDEX IF NOT EXISTS idx_ai_policies_audits_tenant
    ON aihelms.ai_policies_audits (tenant_id);
