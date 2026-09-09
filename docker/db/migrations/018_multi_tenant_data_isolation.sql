-- 018: 多租户数据隔离 — 给核心业务表加 tenant_id
-- 覆盖 Phase 2 的 P0 业务表
-- 注: branding/router_settings/ai_policies_settings 的单例改多实例留到 Phase 4 迁移
-- 注: sync_state 的 PK 改造留到后续(涉及 Celery beat 任务名变更,风险大)

-- 1. 核心业务表加 tenant_id
ALTER TABLE aihelms.departments ADD COLUMN IF NOT EXISTS tenant_id BIGINT NOT NULL DEFAULT 1;
ALTER TABLE aihelms.projects ADD COLUMN IF NOT EXISTS tenant_id BIGINT NOT NULL DEFAULT 1;
ALTER TABLE aihelms.ai_keys ADD COLUMN IF NOT EXISTS tenant_id BIGINT NOT NULL DEFAULT 1;
ALTER TABLE aihelms.providers ADD COLUMN IF NOT EXISTS tenant_id BIGINT NOT NULL DEFAULT 1;
ALTER TABLE aihelms.credentials ADD COLUMN IF NOT EXISTS tenant_id BIGINT NOT NULL DEFAULT 1;
ALTER TABLE aihelms.models ADD COLUMN IF NOT EXISTS tenant_id BIGINT NOT NULL DEFAULT 1;
ALTER TABLE aihelms.model_deployments ADD COLUMN IF NOT EXISTS tenant_id BIGINT NOT NULL DEFAULT 1;
ALTER TABLE aihelms.model_access_groups ADD COLUMN IF NOT EXISTS tenant_id BIGINT NOT NULL DEFAULT 1;
ALTER TABLE aihelms.key_scenarios ADD COLUMN IF NOT EXISTS tenant_id BIGINT NOT NULL DEFAULT 1;
ALTER TABLE aihelms.mcp_servers ADD COLUMN IF NOT EXISTS tenant_id BIGINT NOT NULL DEFAULT 1;
ALTER TABLE aihelms.skills ADD COLUMN IF NOT EXISTS tenant_id BIGINT NOT NULL DEFAULT 1;
ALTER TABLE aihelms.agents ADD COLUMN IF NOT EXISTS tenant_id BIGINT NOT NULL DEFAULT 1;
ALTER TABLE aihelms.resource_applications ADD COLUMN IF NOT EXISTS tenant_id BIGINT NOT NULL DEFAULT 1;
ALTER TABLE aihelms.export_tasks ADD COLUMN IF NOT EXISTS tenant_id BIGINT NOT NULL DEFAULT 1;
ALTER TABLE aihelms.efficiency_reports ADD COLUMN IF NOT EXISTS tenant_id BIGINT NOT NULL DEFAULT 1;
ALTER TABLE aihelms.api_keys ADD COLUMN IF NOT EXISTS tenant_id BIGINT NOT NULL DEFAULT 1;

-- 2. 日志表加 tenant_id (nullable, 历史日志无 tenant, 新日志必填)
ALTER TABLE aihelms.llm_call_logs ADD COLUMN IF NOT EXISTS tenant_id BIGINT;
ALTER TABLE aihelms.mcp_call_logs ADD COLUMN IF NOT EXISTS tenant_id BIGINT;
ALTER TABLE aihelms.skill_usage_logs ADD COLUMN IF NOT EXISTS tenant_id BIGINT;
ALTER TABLE aihelms.agent_usage_logs ADD COLUMN IF NOT EXISTS tenant_id BIGINT;

-- 回填历史日志的 tenant_id (通过 user_id 关联 users.tenant_id)
UPDATE aihelms.llm_call_logs l SET tenant_id = u.tenant_id
  FROM aihelms.users u WHERE l.user_id = u.id AND l.tenant_id IS NULL;
UPDATE aihelms.mcp_call_logs m SET tenant_id = u.tenant_id
  FROM aihelms.users u WHERE m.user_id = u.id AND m.tenant_id IS NULL;
UPDATE aihelms.skill_usage_logs s SET tenant_id = u.tenant_id
  FROM aihelms.users u WHERE s.user_id = u.id AND s.tenant_id IS NULL;
UPDATE aihelms.agent_usage_logs a SET tenant_id = u.tenant_id
  FROM aihelms.users u WHERE a.user_id = u.id AND a.tenant_id IS NULL;

-- 3. cost_summary_daily 加 tenant_id (聚合表,影响面最大)
ALTER TABLE aihelms.cost_summary_daily ADD COLUMN IF NOT EXISTS tenant_id BIGINT NOT NULL DEFAULT 1;

-- 4. user_departments / user_projects 加冗余 tenant_id (加速查询)
ALTER TABLE aihelms.user_departments ADD COLUMN IF NOT EXISTS tenant_id BIGINT NOT NULL DEFAULT 1;
ALTER TABLE aihelms.user_projects ADD COLUMN IF NOT EXISTS tenant_id BIGINT NOT NULL DEFAULT 1;

-- 5. 索引(加速 tenant 过滤)
CREATE INDEX IF NOT EXISTS idx_departments_tenant ON aihelms.departments (tenant_id);
CREATE INDEX IF NOT EXISTS idx_projects_tenant ON aihelms.projects (tenant_id);
CREATE INDEX IF NOT EXISTS idx_ai_keys_tenant ON aihelms.ai_keys (tenant_id);
CREATE INDEX IF NOT EXISTS idx_providers_tenant ON aihelms.providers (tenant_id);
CREATE INDEX IF NOT EXISTS idx_credentials_tenant ON aihelms.credentials (tenant_id);
CREATE INDEX IF NOT EXISTS idx_models_tenant ON aihelms.models (tenant_id);
CREATE INDEX IF NOT EXISTS idx_model_deployments_tenant ON aihelms.model_deployments (tenant_id);
CREATE INDEX IF NOT EXISTS idx_mcp_servers_tenant ON aihelms.mcp_servers (tenant_id);
CREATE INDEX IF NOT EXISTS idx_skills_tenant ON aihelms.skills (tenant_id);
CREATE INDEX IF NOT EXISTS idx_agents_tenant ON aihelms.agents (tenant_id);
CREATE INDEX IF NOT EXISTS idx_resource_applications_tenant ON aihelms.resource_applications (tenant_id);
CREATE INDEX IF NOT EXISTS idx_export_tasks_tenant ON aihelms.export_tasks (tenant_id);
CREATE INDEX IF NOT EXISTS idx_efficiency_reports_tenant ON aihelms.efficiency_reports (tenant_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_tenant ON aihelms.api_keys (tenant_id);
CREATE INDEX IF NOT EXISTS idx_llm_logs_tenant ON aihelms.llm_call_logs (tenant_id);
CREATE INDEX IF NOT EXISTS idx_mcp_logs_tenant ON aihelms.mcp_call_logs (tenant_id);
CREATE INDEX IF NOT EXISTS idx_cost_summary_tenant ON aihelms.cost_summary_daily (tenant_id);
CREATE INDEX IF NOT EXISTS idx_user_departments_tenant ON aihelms.user_departments (tenant_id);
CREATE INDEX IF NOT EXISTS idx_user_projects_tenant ON aihelms.user_projects (tenant_id);
