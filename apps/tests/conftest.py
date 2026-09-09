"""多租户测试共享 fixture

提供构造不同租户用户/资源的辅助函数，供隔离测试复用。
不依赖真实数据库，全部用 mock 对象。
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest


def make_user(
    user_id: int = 1,
    tenant_id: int = 1,
    is_super_admin: bool = False,
    is_tenant_admin: bool = False,
    is_admin: bool = False,
    username: str = "testuser",
) -> SimpleNamespace:
    """构造一个带 tenant_id 的假 User ORM 对象。"""
    return SimpleNamespace(
        id=user_id,
        username=username,
        email=f"{username}@test.com",
        tenant_id=tenant_id,
        is_admin=is_admin,
        is_super_admin=is_super_admin,
        is_tenant_admin=is_tenant_admin,
        is_active=True,
        roles=[],
        departments=[],
    )


def make_current_user(
    user_id: int = 1,
    tenant_id: int | None = 1,
    is_super_admin: bool = False,
    is_tenant_admin: bool = False,
    permissions: list[str] | None = None,
) -> dict:
    """构造一个模拟 JWT 解码后的 current_user dict（API 层用）。"""
    return {
        "id": user_id,
        "username": "testuser",
        "identity_type": "user",
        "is_admin": is_super_admin or is_tenant_admin,
        "is_super_admin": is_super_admin,
        "is_tenant_admin": is_tenant_admin,
        "tenant_id": tenant_id,
        "permissions": permissions or [],
    }


def make_mock_session_with_rows(rows: list) -> AsyncMock:
    """构造一个假 AsyncSession，execute 返回指定 rows（用于断言 SQL 字符串）。

    用法:
        session = make_mock_session_with_rows([row1, row2])
        result = await repo.find_all(session, ..., tenant_id=5)
        sql = str(session.execute.await_args.args[0])
        assert "tenant_id" in sql
    """
    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = rows
    result.scalar_one_or_none.return_value = rows[0] if rows else None
    result.scalar_one.return_value = rows[0] if rows else None
    session.execute.return_value = result
    return session


def make_mock_session_with_count(count: int) -> AsyncMock:
    """构造一个假 AsyncSession，execute 返回一个 count 值。"""
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one.return_value = count
    session.execute.return_value = result
    return session
