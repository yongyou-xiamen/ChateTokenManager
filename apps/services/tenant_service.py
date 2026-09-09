from sqlalchemy.ext.asyncio import AsyncSession

from exceptions import ConflictError, NotFoundError
from models.db import Tenant
from repositories import tenant_repo


async def list_tenants(
    session: AsyncSession, page: int, page_size: int, keyword: str = ""
) -> tuple[list[dict], int]:
    tenants, total = await tenant_repo.list_tenants(session, page, page_size, keyword)
    items = []
    for t in tenants:
        user_count = await tenant_repo.count_users_by_tenant(session, t.id)
        items.append(_to_dict(t, user_count))
    return items, total


async def get_tenant(session: AsyncSession, tenant_id: int) -> dict:
    tenant = await tenant_repo.find_by_id(session, tenant_id)
    if not tenant:
        raise NotFoundError("tenant", tenant_id)
    user_count = await tenant_repo.count_users_by_tenant(session, tenant_id)
    return _to_dict(tenant, user_count)


async def get_current_tenant(session: AsyncSession, tenant_id: int) -> dict:
    return await get_tenant(session, tenant_id)


async def create_tenant(
    session: AsyncSession, name: str, slug: str, settings: dict | None = None
) -> dict:
    existing = await tenant_repo.find_by_slug(session, slug)
    if existing:
        raise ConflictError(f"租户 slug 已存在: {slug}")
    tenant = Tenant(name=name, slug=slug, status="active", settings=settings or {})
    tenant = await tenant_repo.create_tenant(session, tenant)
    await session.commit()
    return _to_dict(tenant, 0)


async def update_tenant(
    session: AsyncSession, tenant_id: int, **fields: object
) -> dict:
    tenant = await tenant_repo.find_by_id(session, tenant_id)
    if not tenant:
        raise NotFoundError("tenant", tenant_id)
    if "slug" in fields and fields["slug"] != tenant.slug:
        existing = await tenant_repo.find_by_slug(session, str(fields["slug"]))
        if existing:
            raise ConflictError(f"租户 slug 已存在: {fields['slug']}")
    tenant = await tenant_repo.update_tenant(session, tenant, **fields)
    await session.commit()
    user_count = await tenant_repo.count_users_by_tenant(session, tenant_id)
    return _to_dict(tenant, user_count)


async def update_tenant_status(
    session: AsyncSession, tenant_id: int, status: str
) -> dict:
    if status not in ("active", "suspended"):
        raise ConflictError(f"无效的租户状态: {status}")
    return await update_tenant(session, tenant_id, status=status)


def _to_dict(tenant: Tenant, user_count: int = 0) -> dict:
    return {
        "id": tenant.id,
        "name": tenant.name,
        "slug": tenant.slug,
        "status": tenant.status,
        "settings": tenant.settings or {},
        "user_count": user_count,
        "created_at": str(tenant.created_at) if tenant.created_at else None,
        "updated_at": str(tenant.updated_at) if tenant.updated_at else None,
    }
