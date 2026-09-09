"""多租户过滤工具

提供统一的 tenant_id 过滤逻辑，供所有 Repository 使用。
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.db import Base


def apply_tenant_filter(stmt, model, tenant_id: int | None, *, skip: bool = False):
    """给查询语句加 tenant_id 过滤。

    skip=True 用于平台超管跨租户查询(tenant_id 也会被忽略)。
    如果模型没有 tenant_id 列,直接返回原语句(字典表等)。
    """
    if skip or tenant_id is None:
        return stmt
    if hasattr(model, "tenant_id"):
        return stmt.where(model.tenant_id == tenant_id)
    return stmt
