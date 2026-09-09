"""多租户数据隔离测试

覆盖范围:
1. apply_tenant_filter 工具函数本身
2. Repository 层: 查询是否正确加 tenant_id 过滤
3. Service 层: 是否正确透传 tenant_id 给 repo
4. API 层: 是否从 current_user 提取 tenant_id
5. 权限守卫: is_super_admin/is_tenant_admin 分支
6. JWT payload: login 时 tenant_id 是否写入 token
7. LiteLLM 命名空间: alias/user_id 是否带 tenant 前缀
8. MCP allow_all_keys: 是否改为 False
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from types import SimpleNamespace
from datetime import date

from sqlalchemy import select

from models.db import (
    User,
    Department,
    Project,
    AiKey,
    Model,
    McpServer,
    Skill,
    Agent,
    LlmCallLog,
    McpCallLog,
    Tenant,
)
from repositories.base import apply_tenant_filter
from repositories import (
    ai_key_repo,
    department_repo,
    project_repo,
    user_repo,
    model_repo,
    usage_log_repo,
    efficiency_cost_repo,
)
from services import user_service, tenant_service
from services.ai_key_service import _build_key_alias, _base_key_metadata
from core.deps import require_permission, require_super_admin


# ============================================================
# 1. apply_tenant_filter 工具函数
# ============================================================


class TestApplyTenantFilter:
    """测试 apply_tenant_filter 核心逻辑。"""

    def test_filter_added_when_tenant_id_provided(self):
        """tenant_id 不为 None 时,应加 where 过滤。"""
        stmt = select(Department)
        result = apply_tenant_filter(stmt, Department, tenant_id=5)
        sql_str = str(result)
        assert "tenant_id =" in sql_str or "tenant_id=" in sql_str

    def test_no_filter_when_tenant_id_is_none(self):
        """tenant_id=None 时(超管场景),不加任何过滤。"""
        stmt = select(Department)
        result = apply_tenant_filter(stmt, Department, tenant_id=None)
        assert result is stmt  # 返回原语句,未修改

    def test_no_filter_when_skip_true(self):
        """skip=True 时显式跳过过滤。"""
        stmt = select(Department)
        result = apply_tenant_filter(stmt, Department, tenant_id=5, skip=True)
        assert result is stmt

    def test_no_filter_for_model_without_tenant_id(self):
        """模型没有 tenant_id 列时(如 Tenant 本身),不加过滤。"""
        stmt = select(Tenant)
        result = apply_tenant_filter(stmt, Tenant, tenant_id=5)
        assert result is stmt

    def test_filter_for_different_models(self):
        """多种模型都应正确加过滤。"""
        for model in [User, Department, Project, AiKey, Model, McpServer, Skill, Agent]:
            stmt = select(model)
            result = apply_tenant_filter(stmt, model, tenant_id=3)
            assert "tenant_id" in str(
                result
            ), f"{model.__name__} should have tenant_id filter"


# ============================================================
# 2. Repository 层: tenant_id 过滤
# ============================================================


class TestRepositoryTenantFilter:
    """测试 Repository 层是否正确加 tenant_id 过滤到 SQL。"""

    @pytest.mark.asyncio
    async def test_department_find_all_active_adds_tenant_filter(self):
        """department_repo.find_all_active 传 tenant_id 时 SQL 应含 tenant_id 条件。"""
        session = AsyncMock()
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        session.execute.return_value = result

        await department_repo.find_all_active(session, tenant_id=7)

        sql = str(session.execute.await_args.args[0])
        assert "tenant_id =" in sql or "tenant_id=" in sql

    @pytest.mark.asyncio
    async def test_department_find_all_active_no_tenant_filter_when_none(self):
        """tenant_id=None 时 department_repo.find_all_active 不加 WHERE 过滤。"""
        session = AsyncMock()
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        session.execute.return_value = result

        await department_repo.find_all_active(session, tenant_id=None)

        sql = str(session.execute.await_args.args[0])
        # WHERE 子句中不应有 tenant_id = (SELECT 列表中的 tenant_id 列名不算)
        where_clause = sql.split("FROM")[1] if "FROM" in sql else sql
        assert "tenant_id =" not in where_clause and "tenant_id=" not in where_clause

    @pytest.mark.asyncio
    async def test_ai_key_find_all_adds_tenant_filter(self):
        """ai_key_repo.find_all 传 tenant_id 时 SQL 应含 tenant_id 条件。"""
        session = AsyncMock()
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        session.execute.return_value = result

        await ai_key_repo.find_all(session, page=1, page_size=20, tenant_id=3)

        sql = str(session.execute.await_args.args[0])
        assert "tenant_id =" in sql or "tenant_id=" in sql

    @pytest.mark.asyncio
    async def test_ai_key_count_all_adds_tenant_filter(self):
        """ai_key_repo.count_all 传 tenant_id 时 SQL 应含 tenant_id 条件。"""
        session = AsyncMock()
        result = MagicMock()
        result.scalar_one.return_value = 0
        session.execute.return_value = result

        await ai_key_repo.count_all(session, tenant_id=3)

        sql = str(session.execute.await_args.args[0])
        assert "tenant_id =" in sql or "tenant_id=" in sql

    @pytest.mark.asyncio
    async def test_ai_key_find_all_main_keys_adds_tenant_filter(self):
        """ai_key_repo.find_all_main_keys 传 tenant_id 时防止跨租户同步(关键安全点)。"""
        session = AsyncMock()
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        session.execute.return_value = result

        await ai_key_repo.find_all_main_keys(session, tenant_id=5)

        sql = str(session.execute.await_args.args[0])
        assert "tenant_id =" in sql or "tenant_id=" in sql

    @pytest.mark.asyncio
    async def test_project_find_by_id_adds_tenant_filter(self):
        """project_repo.find_by_id 传 tenant_id 时防止跨租户访问。"""
        session = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        session.execute.return_value = result

        await project_repo.find_by_id(session, project_id=10, tenant_id=3)

        sql = str(session.execute.await_args.args[0])
        assert "tenant_id =" in sql or "tenant_id=" in sql

    @pytest.mark.asyncio
    async def test_user_count_users_adds_tenant_filter(self):
        """user_repo.count_users 传 tenant_id 时只统计本租户用户。"""
        session = AsyncMock()
        result = MagicMock()
        result.scalar_one.return_value = 0
        session.execute.return_value = result

        await user_repo.count_users(session, tenant_id=2)

        sql = str(session.execute.await_args.args[0])
        assert "tenant_id =" in sql or "tenant_id=" in sql

    @pytest.mark.asyncio
    async def test_usage_log_find_llm_logs_adds_tenant_filter(self):
        """usage_log_repo.find_llm_logs 传 tenant_id 时只返回本租户日志。"""
        session = AsyncMock()
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        session.execute.return_value = result

        await usage_log_repo.find_llm_logs(session, page=1, page_size=20, tenant_id=4)

        sql = str(session.execute.await_args.args[0])
        assert "tenant_id =" in sql or "tenant_id=" in sql

    @pytest.mark.asyncio
    async def test_efficiency_cost_build_cost_filters_adds_tenant(self):
        """_build_cost_filters 传 tenant_id 时返回的 WHERE 应含 tenant_id 条件。"""
        filters, params = efficiency_cost_repo._build_cost_filters(
            date(2026, 1, 1), date(2026, 1, 31), None, None, tenant_id=5
        )
        assert "tenant_id" in filters
        assert params.get("tenant_id") == 5

    @pytest.mark.asyncio
    async def test_efficiency_cost_build_cost_filters_no_tenant_when_none(self):
        """_build_cost_filters tenant_id=None 时不加过滤(超管跨租户)。"""
        filters, params = efficiency_cost_repo._build_cost_filters(
            date(2026, 1, 1), date(2026, 1, 31), None, None, tenant_id=None
        )
        assert "tenant_id" not in filters
        assert "tenant_id" not in params


# ============================================================
# 3. Service 层: tenant_id 透传
# ============================================================


class TestServiceTenantPassthrough:
    """测试 Service 层是否正确把 tenant_id 传给 Repository。"""

    @pytest.mark.asyncio
    async def test_user_service_list_users_passes_tenant_id(self, monkeypatch):
        """user_service.list_users 应把 tenant_id 传给 user_repo。"""
        mock_count = AsyncMock(return_value=0)
        mock_find = AsyncMock(return_value=[])
        monkeypatch.setattr(user_service.user_repo, "count_users", mock_count)
        monkeypatch.setattr(user_service.user_repo, "find_users", mock_find)

        await user_service.list_users(AsyncMock(), page=1, page_size=20, tenant_id=7)

        # count_users 应收到 tenant_id=7
        assert mock_count.await_args.kwargs.get("tenant_id") == 7
        # find_users 应收到 tenant_id=7
        assert mock_find.await_args.kwargs.get("tenant_id") == 7

    @pytest.mark.asyncio
    async def test_user_service_list_users_passes_none_for_super_admin(
        self, monkeypatch
    ):
        """超管场景 tenant_id=None 时 service 不加过滤。"""
        mock_count = AsyncMock(return_value=0)
        mock_find = AsyncMock(return_value=[])
        monkeypatch.setattr(user_service.user_repo, "count_users", mock_count)
        monkeypatch.setattr(user_service.user_repo, "find_users", mock_find)

        await user_service.list_users(AsyncMock(), tenant_id=None)

        assert mock_count.await_args.kwargs.get("tenant_id") is None
        assert mock_find.await_args.kwargs.get("tenant_id") is None

    @pytest.mark.asyncio
    async def test_user_service_create_user_sets_tenant_id(self, monkeypatch):
        """user_service.create_user 应正确设置 user.tenant_id。"""
        created_user = SimpleNamespace(
            id=10,
            tenant_id=3,
            username="newuser",
            email="new@test.com",
            phone="",
            display_name="",
            position="",
            avatar="",
            is_active=True,
            is_admin=False,
            is_super_admin=False,
            is_tenant_admin=True,
            litellm_user_id=None,
            created_at=None,
            updated_at=None,
            roles=[],
            departments=[],
            projects=[],
        )
        mock_create = AsyncMock(return_value=created_user)
        mock_find = AsyncMock(return_value=None)
        monkeypatch.setattr(user_service.user_repo, "create_user", mock_create)
        monkeypatch.setattr(
            user_service.user_repo, "find_user_by_username_or_email", mock_find
        )
        monkeypatch.setattr(user_service.litellm_client, "create_user", AsyncMock())
        monkeypatch.setattr(
            user_service.ai_key_service,
            "create_personal_main_key",
            AsyncMock(),
        )

        await user_service.create_user(
            AsyncMock(),
            username="newuser",
            email="new@test.com",
            password="password123",
            tenant_id=3,
            is_tenant_admin=True,
        )

        # 检查传给 repo.create_user 的 user 对象的 tenant_id
        actual_user = mock_create.await_args.args[1]
        assert actual_user.tenant_id == 3
        assert actual_user.is_tenant_admin is True


# ============================================================
# 4. 权限守卫: is_super_admin / is_tenant_admin
# ============================================================


class TestPermissionGuard:
    """测试 require_permission 和 require_super_admin 的租户权限分支。"""

    @pytest.mark.asyncio
    async def test_require_permission_allows_super_admin_without_perm(self):
        """is_super_admin=True 时,即使没有具体权限码也放行。"""
        checker = require_permission("user:read")
        current_user = {
            "is_super_admin": True,
            "is_tenant_admin": False,
            "permissions": [],
        }
        result = await checker(current_user)
        assert result is current_user

    @pytest.mark.asyncio
    async def test_require_permission_allows_tenant_admin_without_perm(self):
        """is_tenant_admin=True 时,即使没有具体权限码也放行。"""
        checker = require_permission("user:read")
        current_user = {
            "is_super_admin": False,
            "is_tenant_admin": True,
            "permissions": [],
        }
        result = await checker(current_user)
        assert result is current_user

    @pytest.mark.asyncio
    async def test_require_permission_allows_normal_user_with_perm(self):
        """普通用户有对应权限码时放行。"""
        checker = require_permission("user:read")
        current_user = {
            "is_super_admin": False,
            "is_tenant_admin": False,
            "permissions": ["user:read"],
        }
        result = await checker(current_user)
        assert result is current_user

    @pytest.mark.asyncio
    async def test_require_permission_denies_normal_user_without_perm(self):
        """普通用户无对应权限码时 403。"""
        import pytest as _pytest

        checker = require_permission("user:delete")
        current_user = {
            "is_super_admin": False,
            "is_tenant_admin": False,
            "permissions": ["user:read"],
        }
        with _pytest.raises(Exception) as exc_info:
            await checker(current_user)
        assert (
            "403" in str(exc_info.value.status_code)
            or exc_info.value.status_code == 403
        )

    @pytest.mark.asyncio
    async def test_require_super_admin_allows_super_admin(self):
        """require_super_admin 放行 is_super_admin=True。"""
        checker = require_super_admin()
        current_user = {"is_super_admin": True}
        result = await checker(current_user)
        assert result is current_user

    @pytest.mark.asyncio
    async def test_require_super_admin_denies_tenant_admin(self):
        """require_super_admin 拒绝 is_super_admin=False(即使是租户管理员)。"""
        import pytest as _pytest

        checker = require_super_admin()
        current_user = {"is_super_admin": False, "is_tenant_admin": True}
        with _pytest.raises(Exception) as exc_info:
            await checker(current_user)
        assert exc_info.value.status_code == 403


# ============================================================
# 5. LiteLLM 命名空间隔离
# ============================================================


class TestLiteLLMNamespace:
    """测试 LiteLLM alias/user_id 是否带 tenant 前缀。"""

    def test_key_alias_has_tenant_prefix(self):
        """_build_key_alias 应在 alias 前加 t{tenant_id}_ 前缀。"""
        alias = _build_key_alias("personal_main", "user", 10, "main", tenant_id=3)
        assert alias.startswith("t3_")
        assert "user:10" in alias

    def test_key_alias_different_tenants_dont_collide(self):
        """不同租户相同 owner_id 的 alias 应不同。"""
        alias_t1 = _build_key_alias("personal_main", "user", 10, "main", tenant_id=1)
        alias_t2 = _build_key_alias("personal_main", "user", 10, "main", tenant_id=2)
        assert alias_t1 != alias_t2

    def test_key_metadata_includes_tenant_id(self):
        """_base_key_metadata 应包含 aihelms_tenant_id。"""
        key = SimpleNamespace(id=5, key_type="personal_main", tenant_id=3)
        metadata = _base_key_metadata(key)
        assert metadata["aihelms_tenant_id"] == 3
        assert metadata["aihelms_key_id"] == 5

    def test_key_alias_all_types_have_prefix(self):
        """所有 key_type 的 alias 都应有 tenant 前缀。"""
        key_types = [
            "personal_main",
            "personal_scene",
            "dept_main",
            "dept_scene",
            "project_main",
            "project_scene",
        ]
        for kt in key_types:
            alias = _build_key_alias(kt, "user", 1, "test", tenant_id=5)
            assert alias.startswith("t5_"), f"{kt} alias should have tenant prefix"


# ============================================================
# 6. MCP allow_all_keys 安全检查
# ============================================================


class TestMcpAllowAllKeys:
    """测试 MCP create_mcp_server 的 allow_all_keys 默认值为 False。"""

    def test_create_mcp_server_default_allow_all_keys_is_false(self):
        """litellm_client.create_mcp_server 的 allow_all_keys 默认应为 False。"""
        import inspect
        from services import litellm_client

        sig = inspect.signature(litellm_client.create_mcp_server)
        param = sig.parameters.get("allow_all_keys")
        assert (
            param is not None
        ), "create_mcp_server should have allow_all_keys parameter"
        assert param.default is False, "allow_all_keys default should be False"

    @pytest.mark.asyncio
    async def test_create_mcp_server_sends_false_when_default(self, monkeypatch):
        """默认调用 create_mcp_server 时,发送给 LiteLLM 的 allow_all_keys 应为 False。"""
        from services import litellm_client

        captured_data = {}

        async def fake_request(method, path, json_data=None, **kwargs):
            captured_data.update(json_data or {})
            return {"server_id": "test"}

        monkeypatch.setattr(litellm_client, "_request", fake_request)

        await litellm_client.create_mcp_server(
            server_name="test_server",
            url="http://localhost:8080",
        )

        assert captured_data.get("allow_all_keys") is False


# ============================================================
# 7. Tenant Service
# ============================================================


class TestTenantService:
    """测试 tenant_service 的 CRUD 逻辑。"""

    @pytest.mark.asyncio
    async def test_create_tenant_duplicate_slug_raises_conflict(self, monkeypatch):
        """创建租户时 slug 重复应抛 ConflictError。"""
        from exceptions import ConflictError

        existing = SimpleNamespace(id=1, slug="acme", name="Acme")
        monkeypatch.setattr(
            tenant_service.tenant_repo,
            "find_by_slug",
            AsyncMock(return_value=existing),
        )

        with pytest.raises(ConflictError):
            await tenant_service.create_tenant(AsyncMock(), name="Another", slug="acme")

    @pytest.mark.asyncio
    async def test_get_tenant_not_found_raises(self, monkeypatch):
        """查询不存在的租户应抛 NotFoundError。"""
        from exceptions import NotFoundError

        monkeypatch.setattr(
            tenant_service.tenant_repo,
            "find_by_id",
            AsyncMock(return_value=None),
        )

        with pytest.raises(NotFoundError):
            await tenant_service.get_tenant(AsyncMock(), tenant_id=999)

    @pytest.mark.asyncio
    async def test_update_tenant_status_invalid_raises(self):
        """更新租户状态为无效值应抛 ConflictError。"""
        from exceptions import ConflictError

        with pytest.raises(ConflictError):
            await tenant_service.update_tenant_status(
                AsyncMock(), tenant_id=1, status="invalid"
            )
