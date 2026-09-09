# AIHelms 多租户改造方案

> **版本**: v1.0
> **状态**: 草案
> **作者**: ——
> **更新**: 2026-09-08

## 一、目标与范围

### 1.1 业务目标

将 AIHelms 从单租户平台改造为多租户平台,支持:
- 多个独立组织(租户)共享一套部署,数据彼此隔离
- 每个租户独立管理自己的用户、部门、项目、AI 资源
- 每个租户独立的品牌定制(白标)
- 平台超管统一管理所有租户

### 1.2 设计原则

| 原则 | 说明 |
|------|------|
| 行级隔离 | 所有业务表加 `tenant_id` 列,共享 schema,改动最小,运维简单 |
| 一用户一租户 | 用户注册时绑定租户,不支持跨租户(简化前端,无需切换器) |
| 租户独立纳管 | 每租户自己接入供应商、凭证、模型(不共享模型池) |
| 每租户独立品牌 | Branding 从单例改为 per-tenant,支持白标 |
| 平滑迁移 | 现有数据归入默认租户(tenant_id=1),不丢失、不停机 |

### 1.3 不在本次范围

- 跨租户资源共享(模型市场共享池)
- 租户级计费/订阅
- 细粒度 IP 白名单/网络隔离
- SSO 按租户配置(后续迭代)

---

## 二、核心数据模型

### 2.1 新增 Tenant 表

```python
# apps/models/db.py
class Tenant(Base):
    __tablename__ = "tenants"
    __table_args__ = {"schema": "aihelms"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(Text, unique=True, nullable=False)  # URL 标识
    status: Mapped[str] = mapped_column(Text, default="active")  # active/suspended
    settings: Mapped[dict] = mapped_column(JSONB, default=dict)  # 租户级配置
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
```

### 2.2 User 表改造

```python
class User(Base):
    # 新增
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("aihelms.tenants.id"), nullable=False
    )
    is_tenant_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    # 保留 is_super_admin(平台超管,跨租户)
    # 移除 is_admin(由 is_tenant_admin 替代)
```

**权限层级**:

```
平台超管 (is_super_admin=True)
  ├─ 创建/停用租户
  ├─ 指定租户管理员
  └─ 跨租户审计

租户管理员 (is_tenant_admin=True)
  ├─ 本租户用户/部门/项目管理
  ├─ 本租户模型/凭证/MCP/Skill 纳管
  ├─ 本租户 AI Key 签发与预算
  └─ 本租户成本/效能/审计查看

普通用户
  └─ 仅访问自己有权限的资源
```

### 2.3 业务表 tenant_id 改造清单

#### P0 — 核心业务表(必须改造)

| 表 | 改造 | 说明 |
|---|---|---|
| `users` | + tenant_id (FK), + is_tenant_admin | 用户主体 |
| `departments` | + tenant_id | 部门树 |
| `projects` | + tenant_id | 项目 |
| `ai_keys` | + tenant_id | AI 身份 |
| `ai_key_model_limits` | 通过 ai_key_id 间接隔离 | 可选冗余 tenant_id 加速查询 |
| `providers` | + tenant_id | 供应商 |
| `credentials` | + tenant_id | 凭证 |
| `models` | + tenant_id | 模型 |
| `model_deployments` | 通过 model_id 间接隔离 | |
| `model_access_groups` | + tenant_id | 访问组 |
| `model_department_visibility` | + tenant_id | 可见性 |
| `model_user_visibility` | + tenant_id | 可见性 |
| `mcp_servers` | + tenant_id | MCP |
| `mcp_tools` | 通过 server_id 间接隔离 | |
| `skills` | + tenant_id | Skill |
| `agents` | + tenant_id | 智能体 |
| `llm_call_logs` | + tenant_id (冗余) | 加速查询 |
| `mcp_call_logs` | + tenant_id | |
| `skill_usage_logs` | + tenant_id | |
| `agent_usage_logs` | + tenant_id | |
| `cost_summary_daily` | + tenant_id,改唯一索引 | 预聚合 |
| `resource_applications` | + tenant_id | 资源申请 |
| `export_tasks` | + tenant_id | 导出任务 |
| `admin_audit_logs` | + tenant_id | 审计日志 |
| `efficiency_reports` | + tenant_id | 效能报告 |
| `efficiency_suggestions` | 通过 report_id 间接隔离 | |

#### P1 — 配置类(单例改多实例)

| 表 | 当前 | 改造 |
|---|---|---|
| `branding` | 单例 (CHECK id=1) | 删 singleton 约束,+ tenant_id,改多实例 |
| `router_settings` | 单例 | + tenant_id,改多实例 |
| `ai_policies_settings` | 单例 | + tenant_id,改多实例 |
| `ai_policies_audits` | 全局 | + tenant_id |
| `api_keys` | 平台服务 Key | + tenant_id |

#### P2 — 字典表(保持平台共享)

| 表 | 原因 |
|---|---|
| `permissions` | 全局权限字典 |
| `provider_prefix_map` | 技术路由映射 |
| `ai_policies_risk_catalog` | 风险目录 |
| `business_scenarios` | 业务场景字典 |
| `key_scenarios` | Key 场景字典 |
| `mcp_categories` / `skill_categories` / `agent_categories` / `agent_platforms` | 分类字典 |

#### P3 — 角色策略

| 表 | 改造 |
|---|---|
| `roles` | + tenant_id (nullable)。`is_system=True` 系统角色 tenant_id=NULL 全局共享;`is_system=False` 自定义角色按租户隔离 |
| `role_permissions` | 通过 role_id 间接隔离 |
| `user_roles` | + tenant_id,确保用户角色绑定在租户内 |

#### P4 — 同步状态

| 表 | 改造 |
|---|---|
| `sync_state` | 不加列,改 key 命名:`t{tenant_id}_llm_log_sync` |

---

## 三、权限体系

### 3.1 身份模型

```python
# get_current_user 返回结构
{
    "id": 123,
    "username": "alice",
    "tenant_id": 5,
    "tenant_slug": "acme",
    "is_super_admin": False,
    "is_tenant_admin": True,
    "permissions": ["user:read", "model:read", ...],
    "identity_type": "user"
}
```

### 3.2 认证流程

```
请求 (Authorization: Bearer <jwt>)
  │
  ▼
JWT decode → payload 含 {sub, username, tenant_id, is_super_admin, is_tenant_admin, permissions}
  │
  ▼
注入 request.state.tenant_id
  │
  ▼
require_permission(code):
  - is_super_admin=True → 全局放行
  - is_tenant_admin=True → 本租户内放行
  - code in permissions → 本租户内放行
  - 否则 403
```

### 3.3 关键改造点

| 文件 | 行号 | 改动 |
|---|---|---|
| `apps/core/deps.py` | 24-36 | `get_current_user` 返回 tenant_id/is_tenant_admin |
| `apps/core/deps.py` | 85-93 | `require_permission` 增加 tenant 上下文 |
| `apps/services/auth_service.py` | 39-47 | `get_user_permissions` join 时按 tenant 过滤角色 |
| `apps/services/auth_service.py` | 88-125 | `ensure_super_admin` 保留,只创建平台超管 |
| `apps/services/auth_service.py` login | — | JWT payload 加 tenant_id |

---

## 四、隔离中间件

### 4.1 新增 TenantContextMiddleware

```python
# apps/core/tenant.py (新建)
from starlette.middleware.base import BaseHTTPMiddleware

class TenantContextMiddleware(BaseHTTPMiddleware):
    """解析 JWT 注入 tenant 上下文到 request.state"""
    async def dispatch(self, request, call_next):
        # 跳过公开端点
        if request.url.path in {"/api/health", "/api/v1/auth/login", "/api/v1/config/public"}:
            return await call_next(request)
        # 解析 token(可选,失败不阻断)
        user = await get_current_user_optional(request)
        if user:
            request.state.tenant_id = user["tenant_id"]
            request.state.is_super_admin = user["is_super_admin"]
            request.state.current_user = user
        return await call_next(request)
```

### 4.2 在 main.py 注册

```python
# apps/main.py
app.add_middleware(TenantContextMiddleware)  # 在 AuditLogMiddleware 之前
app.add_middleware(AuditLogMiddleware)
```

---

## 五、Repository 层改造

### 5.1 统一过滤工具

```python
# apps/repositories/base.py (新建)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

def apply_tenant_filter(stmt, model, tenant_id: int | None, *, skip: bool = False):
    """统一加 tenant_id 过滤。
    skip=True 用于平台超管跨租户查询。"""
    if skip or tenant_id is None:
        return stmt
    if hasattr(model, "tenant_id"):
        return stmt.where(model.tenant_id == tenant_id)
    return stmt
```

### 5.2 改造模式

每个 repository 的 `list_*`/`get_*` 方法统一调用:

```python
# 改造前
async def list_users(session, page, page_size):
    result = await session.execute(select(User).order_by(User.id))
    return list(result.scalars().all())

# 改造后
async def list_users(session, tenant_id, page, page_size):
    stmt = select(User).order_by(User.id)
    stmt = apply_tenant_filter(stmt, User, tenant_id)
    result = await session.execute(stmt)
    return list(result.scalars().all())
```

**涉及约 20 个 repository 文件**,改动模式一致。

---

## 六、服务层改造

### 6.1 关键服务改动

| 服务 | 文件 | 改动要点 |
|---|---|---|
| auth | `auth_service.py` | login 返回 tenant;`get_user_permissions` 加 tenant 过滤 |
| user | `user_service.py` | `list_users` 按 tenant 过滤;`create_user` 绑定 tenant_id |
| ai_key | `ai_key_service.py` | `list_keys`/`get_my_keys` 加 tenant 过滤;**`sync_public_resource_to_all_keys` 必须限定本租户 main keys** |
| model/provider/credential | 各 service | CRUD 按 tenant 隔离;LiteLLM 同步加 tenant 前缀 |
| dashboard | `dashboard_service.py` | `_get_resources`/`_get_status` 全部加 tenant 过滤 |
| usage_log | `usage_log_service.py` | `list_*_logs` 按 tenant_id 过滤 |
| efficiency | `efficiency_*_service.py` | 已有 dept/project scope,补 tenant 维度 |
| branding | `branding_service.py` | `get_branding` 按 tenant_id 查询 |
| audit | `core/audit.py` | `AdminAuditLog` 写入时带 tenant_id |
| litellm | `litellm_client.py` | key/team/model 命名加 tenant 前缀 |

### 6.2 重点:sync_public_resource_to_all_keys

```python
# apps/services/ai_key_service.py:661-687
# 改造前:遍历所有 main key(跨租户,危险!)
async def sync_public_resource_to_all_keys(session, ...):
    keys = await ai_key_repo.list_all_main_keys(session)

# 改造后:限定本租户
async def sync_public_resource_to_all_keys(session, tenant_id, ...):
    keys = await ai_key_repo.list_main_keys_by_tenant(session, tenant_id)
```

---

## 七、LiteLLM 集成

### 7.1 命名空间隔离

LiteLLM 单实例共享,通过命名空间隔离:

| 资源 | 命名规则 | 示例 |
|---|---|---|
| LiteLLM User | `t{tenant_id}_user_{id}` | `t5_user_123` |
| LiteLLM Team | `t{tenant_id}_dept_{id}` / `t{tenant_id}_proj_{id}` | `t5_dept_8` |
| LiteLLM Key | `t{tenant_id}_key_{id}` | `t5_key_456` |
| LiteLLM Model | `t{tenant_id}_model_{model_id}` | `t5_model_gpt4` |
| LiteLLM Credential | `t{tenant_id}_cred_{id}` | `t5_cred_3` |

### 7.2 MCP 同步改造

```python
# apps/services/litellm_client.py:374
# 改造前
data["allow_all_keys"] = True

# 改造后:仅允许本租户的 keys
data["allow_all_keys"] = False
data["allowed_key_ids"] = await get_tenant_key_ids(session, tenant_id)
```

### 7.3 现有数据迁移

迁移脚本中批量重命名:
```sql
UPDATE aihelms.users SET litellm_user_id = 't1_user_' || id::text
  WHERE litellm_user_id LIKE 'aihelms_user_%';
-- 同理 team_id、key 等
```

---

## 八、前端改造

### 8.1 类型与状态

```typescript
// ui/packages/shared/src/types/auth.ts
interface CurrentUser {
  id: string
  username: string
  tenant_id: number          // 新增
  tenant_name: string        // 新增
  tenant_slug: string        // 新增
  is_super_admin: boolean
  is_tenant_admin: boolean   // 新增(替代 is_admin)
  permissions: string[]
  roles: string[]
  departments: ...
}
```

### 8.2 前端改动清单

| 文件 | 改动 |
|---|---|
| `shared/src/types/auth.ts` | + tenant 字段,`is_admin` → `is_tenant_admin` |
| `shared/src/composables/useAuth.ts` | 存储 tenant 上下文 |
| `shared/src/composables/usePermission.ts` | `is_tenant_admin` 替代 `is_admin` |
| `admin/src/router/index.ts:220-242` | 守卫检查 `is_tenant_admin`/`is_super_admin` |
| `admin/src/components/HeaderBar.vue` | 显示当前租户名 |
| `admin/src/components/Sidebar.vue` | 平台超管才显示「租户管理」菜单 |
| `web/src/layouts/WebLayout.vue` | 无需大改(一用户一租户) |
| **新增** `admin/src/views/platform/TenantManage.vue` | 平台超管管理租户 |
| **新增** `admin/src/views/platform/TenantForm.vue` | 创建/编辑租户 |
| **新增** `admin/src/api/tenant.ts` (shared) | 租户管理 API |

**无需租户切换器**(一用户一租户),简化前端。

### 8.3 平台管理端

新增 `/platform/tenants` 路由(仅 `is_super_admin` 可见):
- 租户列表(名称、slug、状态、用户数、创建时间)
- 创建/编辑/停用租户
- 指定租户管理员
- 跨租户统计概览

---

## 九、API 端点

### 9.1 平台管理(仅 is_super_admin)

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/platform/tenants` | 租户列表 |
| POST | `/api/v1/platform/tenants` | 创建租户 |
| GET | `/api/v1/platform/tenants/{id}` | 租户详情 |
| PUT | `/api/v1/platform/tenants/{id}` | 编辑租户 |
| PATCH | `/api/v1/platform/tenants/{id}/status` | 停用/启用租户 |
| POST | `/api/v1/platform/tenants/{id}/admins` | 指定租户管理员 |
| GET | `/api/v1/platform/stats` | 跨租户统计 |

### 9.2 租户内(租户管理员)

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/tenant` | 当前租户信息 |
| PUT | `/api/v1/tenant` | 更新租户设置 |

---

## 十、数据库迁移

### 10.1 迁移脚本

新建 `docker/db/migrations/017_multi_tenant.sql`:

```sql
BEGIN;

-- 1. 创建 tenants 表
CREATE TABLE IF NOT EXISTS aihelms.tenants (
    id BIGINT PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    settings JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. 默认租户(承载现有数据)
INSERT INTO aihelms.tenants (id, name, slug, status)
VALUES (1, 'Default', 'default', 'active')
ON CONFLICT (id) DO NOTHING;

-- 3. users 加 tenant_id + is_tenant_admin
ALTER TABLE aihelms.users ADD COLUMN tenant_id BIGINT NOT NULL DEFAULT 1;
ALTER TABLE aihelms.users ADD COLUMN is_tenant_admin BOOLEAN NOT NULL DEFAULT FALSE;
UPDATE aihelms.users SET is_tenant_admin = TRUE WHERE is_admin = TRUE AND is_super_admin = FALSE;
ALTER TABLE aihelms.users ADD CONSTRAINT fk_users_tenant
  FOREIGN KEY (tenant_id) REFERENCES aihelms.tenants(id);

-- 4. 核心业务表加 tenant_id(逐表)
-- 模式相同,这里以 departments 为例
ALTER TABLE aihelms.departments ADD COLUMN tenant_id BIGINT NOT NULL DEFAULT 1;
ALTER TABLE aihelms.projects ADD COLUMN tenant_id BIGINT NOT NULL DEFAULT 1;
ALTER TABLE aihelms.ai_keys ADD COLUMN tenant_id BIGINT NOT NULL DEFAULT 1;
ALTER TABLE aihelms.providers ADD COLUMN tenant_id BIGINT NOT NULL DEFAULT 1;
ALTER TABLE aihelms.credentials ADD COLUMN tenant_id BIGINT NOT NULL DEFAULT 1;
ALTER TABLE aihelms.models ADD COLUMN tenant_id BIGINT NOT NULL DEFAULT 1;
ALTER TABLE aihelms.mcp_servers ADD COLUMN tenant_id BIGINT NOT NULL DEFAULT 1;
ALTER TABLE aihelms.skills ADD COLUMN tenant_id BIGINT NOT NULL DEFAULT 1;
ALTER TABLE aihelms.agents ADD COLUMN tenant_id BIGINT NOT NULL DEFAULT 1;
-- ... 其余表同理

-- 5. 日志表加 tenant_id(冗余,加速查询)
ALTER TABLE aihelms.llm_call_logs ADD COLUMN tenant_id BIGINT;
UPDATE aihelms.llm_call_logs SET tenant_id = (
    SELECT tenant_id FROM aihelms.users WHERE users.id = llm_call_logs.user_id
) WHERE user_id IS NOT NULL;
ALTER TABLE aihelms.llm_call_logs ALTER COLUMN tenant_id SET NOT NULL;
-- 同理 mcp_call_logs / skill_usage_logs / agent_usage_logs

-- 6. cost_summary_daily 加 tenant_id + 改唯一索引
ALTER TABLE aihelms.cost_summary_daily ADD COLUMN tenant_id BIGINT NOT NULL DEFAULT 1;
DROP INDEX IF EXISTS aihelms.idx_cost_summary_unique;
CREATE UNIQUE INDEX idx_cost_summary_unique ON aihelms.cost_summary_daily
    (tenant_id, user_id, ai_key_id, department_id, project_id, model, provider_id, server_id, cost_type, key_type, date);

-- 7. 单例表改多实例
ALTER TABLE aihelms.branding DROP CONSTRAINT IF EXISTS branding_singleton;
ALTER TABLE aihelms.branding ADD COLUMN tenant_id BIGINT NOT NULL DEFAULT 1;
ALTER TABLE aihelms.branding ADD CONSTRAINT uk_branding_tenant UNIQUE (tenant_id);

ALTER TABLE aihelms.router_settings DROP CONSTRAINT IF EXISTS router_settings_singleton;
ALTER TABLE aihelms.router_settings ADD COLUMN tenant_id BIGINT NOT NULL DEFAULT 1;

ALTER TABLE aihelms.ai_policies_settings DROP CONSTRAINT IF EXISTS ai_policies_settings_singleton;
ALTER TABLE aihelms.ai_policies_settings ADD COLUMN tenant_id BIGINT NOT NULL DEFAULT 1;

-- 8. roles 加 tenant_id(nullable,系统角色 NULL)
ALTER TABLE aihelms.roles ADD COLUMN tenant_id BIGINT NULL;
-- 自定义角色(is_system=False)绑定到默认租户
UPDATE aihelms.roles SET tenant_id = 1 WHERE is_system = FALSE;

-- 9. user_roles 加 tenant_id
ALTER TABLE aihelms.user_roles ADD COLUMN tenant_id BIGINT NOT NULL DEFAULT 1;

-- 10. sync_state 改 key 命名
UPDATE aihelms.sync_state SET key = 't1_' || key WHERE key NOT LIKE 't%_';

-- 11. LiteLLM 命名空间迁移
UPDATE aihelms.users SET litellm_user_id = 't1_user_' || id::text
  WHERE litellm_user_id LIKE 'aihelms_user_%';
UPDATE aihelms.departments SET litellm_team_id = 't1_dept_' || id::text
  WHERE litellm_team_id IS NOT NULL AND litellm_team_id NOT LIKE 't%_dept_%';
-- ... 同理 projects、ai_keys、models、credentials

-- 12. 加索引(加速 tenant 过滤)
CREATE INDEX idx_users_tenant ON aihelms.users (tenant_id);
CREATE INDEX idx_ai_keys_tenant ON aihelms.ai_keys (tenant_id);
CREATE INDEX idx_models_tenant ON aihelms.models (tenant_id);
CREATE INDEX idx_llm_logs_tenant ON aihelms.llm_call_logs (tenant_id);
-- ... 其余表同理

COMMIT;
```

### 10.2 回滚脚本

新建 `docker/db/migrations/017_multi_tenant_rollback.sql`(可选):
- 保留 tenant_id 列但移除 NOT NULL 约束
- 恢复 singleton 约束
- 不删数据,保证可回退

### 10.3 迁移策略

| 场景 | 策略 |
|---|---|
| 新部署 | 迁移脚本执行,创建默认租户 |
| 现有部署 | 迁移脚本执行,所有数据 tenant_id=1,平滑过渡 |
| 停机要求 | 迁移可在秒级完成(纯 DDL + UPDATE),无需长时间停机 |

---

## 十一、风险与对策

| 风险 | 等级 | 对策 |
|---|---|---|
| `sync_public_resource_to_all_keys` 跨租户泄漏 | **高** | 改造时第一时间限定 tenant;加单元测试覆盖 |
| `AiKey.owner_type/owner_id` 多态无 FK,tenant_id 应用层注入 | 中 | Repository 层统一 `apply_tenant_filter`,CI 加 lint 规则检查所有 select 是否带过滤 |
| LiteLLM 命名空间迁移失败 | 中 | 迁移脚本幂等;失败可回滚;迁移后跑连通性测试 |
| `api_keys` 与 `ai_keys` 概念混淆 | 中 | 代码 review 时明确区分;`api_keys` 平台超管用,可跨租户;`ai_keys` 必须按 tenant 隔离 |
| 现有数据迁移遗漏 | 低 | 迁移脚本后跑校验 SQL,统计各表 tenant_id IS NULL 的行数 |
| 单例改多实例引发查询异常 | 中 | Branding/RouterSettings 的 `repo.get` 从 `session.get(Model, 1)` 改为 `select by tenant_id` |
| `CostSummaryDaily` 唯一索引变更失败 | 低 | 迁移前先删旧索引,再建新索引;加 `IF EXISTS` |

---

## 十二、实施计划

### 阶段划分

| 阶段 | 内容 | 交付物 | 预估 |
|---|---|---|---|
| **Phase 1: 基础设施** | Tenant 表 + User 改造 + 中间件 + 权限体系 + 迁移脚本 | tenant 表、迁移 SQL、`get_current_user` 带 tenant、`require_permission` 带 tenant | 3-5 天 |
| **Phase 2: 数据隔离** | 28 张表加 tenant_id + Repository 层 `apply_tenant_filter` + 服务层改造 | 所有查询带 tenant 过滤、`sync_public_resource_to_all_keys` 限定本租户 | 5-7 天 |
| **Phase 3: LiteLLM 隔离** | LiteLLM 命名空间 + MCP/Skill 同步逻辑 + 命名迁移脚本 | key/team/model 命名加前缀、MCP `allow_all_keys=False` | 2-3 天 |
| **Phase 4: 配置多实例** | Branding/RouterSettings/AiPoliciesSettings 单例改多实例 | 三个 repo 改 `select by tenant_id`、Branding 支持白标 | 2 天 |
| **Phase 5: 前端改造** | 类型 + 守卫 + HeaderBar + 平台管理页面 | `is_tenant_admin` 替代 `is_admin`、租户管理 CRUD 页面 | 3-4 天 |
| **Phase 6: 测试与上线** | 单元测试 + 集成测试 + 现有数据迁移验证 + 部署 | 测试覆盖、迁移演练、tempo 部署验证 | 2-3 天 |
| **合计** | | | **17-24 天** |

### 里程碑

```
Phase 1 ──────► Phase 2 ──────► Phase 3 ──► Phase 4 ──► Phase 5 ──► Phase 6
基础设施        数据隔离        LiteLLM    配置多实例   前端         测试上线
(3-5d)         (5-7d)         (2-3d)     (2d)        (3-4d)      (2-3d)
   │              │              │           │           │           │
   ▼              ▼              ▼           ▼           ▼           ▼
 可登录         查询带          LiteLLM    白标         平台        生产
 带 tenant     tenant 过滤     隔离完成    多租户       管理页      上线
```

### 验收标准

- [ ] 平台超管可创建/停用租户
- [ ] 租户 A 的用户看不到租户 B 的任何数据(用户/Key/模型/日志/成本)
- [ ] 租户管理员可管理本租户全部资源
- [ ] 每个租户有独立的品牌定制
- [ ] LiteLLM 中 key/team/model 命名带 tenant 前缀,无冲突
- [ ] 现有数据迁移后全部归属默认租户(tenant_id=1)
- [ ] `sync_public_resource_to_all_keys` 只影响本租户
- [ ] 单元测试覆盖 tenant 过滤逻辑

---

## 十三、附录

### 13.1 现有架构关键事实(摸底结论)

- 32 个 ORM 类,均在 `aihelms` schema
- 0 处 `tenant`/`organization`/`workspace` 字眼
- `User` 无 tenant_id,通过 `user_departments`/`user_projects` 多对多关联
- `is_admin` 是全局布尔标志,无"租户管理员"概念
- `AiKey.owner_type/owner_id` 多态归属,无 FK
- `Branding`/`RouterSettings`/`AiPoliciesSettings` 三个单例表
- `Provider`/`Credential`/`Model` 平台级共享,无归属字段
- `Agent` 是唯一带 `department_id`/`project_id` 的资源类
- `sync_public_resource_to_all_keys` 遍历所有 main key(跨租户风险)
- LiteLLM 单实例,`allow_all_keys=True` 默认 MCP 对所有 key 开放

### 13.2 涉及文件清单(约 60 个)

**后端**(约 40 个):
- 新增:`apps/core/tenant.py`、`apps/repositories/base.py`、`apps/repositories/tenant_repo.py`、`apps/services/tenant_service.py`、`apps/api/v1/platform.py`、`apps/api/v1/tenant.py`、`docker/db/migrations/017_multi_tenant.sql`
- 修改:`apps/models/db.py`、`apps/core/deps.py`、`apps/core/audit.py`、`apps/main.py`、`apps/services/auth_service.py`、`apps/services/user_service.py`、`apps/services/ai_key_service.py`、`apps/services/dashboard_service.py`、`apps/services/usage_log_service.py`、`apps/services/efficiency_*.py`、`apps/services/branding_service.py`、`apps/services/litellm_client.py`、`apps/services/model_service.py`、`apps/services/provider_service.py`、`apps/services/credential_service.py`、`apps/services/mcp_service.py`、`apps/services/skill_service.py`、`apps/services/agent_service.py`、`apps/repositories/*.py`(约 15 个)、`apps/api/v1/router.py`、`docker/db/init.sql`

**前端**(约 20 个):
- 新增:`ui/packages/admin/src/views/platform/TenantManage.vue`、`ui/packages/admin/src/views/platform/TenantForm.vue`、`ui/packages/shared/src/api/tenant.ts`、`ui/packages/shared/src/types/tenant.ts`
- 修改:`ui/packages/shared/src/types/auth.ts`、`ui/packages/shared/src/composables/useAuth.ts`、`ui/packages/shared/src/composables/usePermission.ts`、`ui/packages/shared/src/index.ts`、`ui/packages/admin/src/router/index.ts`、`ui/packages/admin/src/components/HeaderBar.vue`、`ui/packages/admin/src/components/Sidebar.vue`、`ui/packages/admin/src/layouts/AdminLayout.vue`

### 13.3 术语表

| 术语 | 定义 |
|---|---|
| 租户 (Tenant) | 一个独立的组织实体,拥有独立的用户、资源、配置 |
| 平台超管 (Super Admin) | 跨租户管理者,`is_super_admin=True` |
| 租户管理员 (Tenant Admin) | 租户内管理者,`is_tenant_admin=True` |
| 行级隔离 | 所有业务表加 `tenant_id` 列,查询时过滤 |
| 白标 (Whitelabel) | 每租户独立的品牌定制(名称、Logo、Favicon) |
| LiteLLM 命名空间 | 在 LiteLLM 中通过命名前缀(`t{tenant_id}_`)实现隔离 |
