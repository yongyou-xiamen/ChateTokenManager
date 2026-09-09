from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.db import Tenant, User


async def find_by_id(session: AsyncSession, tenant_id: int) -> Tenant | None:
    return await session.get(Tenant, tenant_id)


async def find_by_slug(session: AsyncSession, slug: str) -> Tenant | None:
    result = await session.execute(select(Tenant).where(Tenant.slug == slug))
    return result.scalar_one_or_none()


async def list_tenants(
    session: AsyncSession, page: int, page_size: int, keyword: str = ""
) -> tuple[list[Tenant], int]:
    stmt = select(Tenant).order_by(Tenant.id)
    count_stmt = select(func.count(Tenant.id))
    if keyword:
        pattern = f"%{keyword}%"
        stmt = stmt.where(Tenant.name.ilike(pattern))
        count_stmt = count_stmt.where(Tenant.name.ilike(pattern))
    offset = (page - 1) * page_size
    stmt = stmt.limit(page_size).offset(offset)
    result = await session.execute(stmt)
    tenants = list(result.scalars().all())
    total = (await session.execute(count_stmt)).scalar_one()
    return tenants, total


async def create_tenant(session: AsyncSession, tenant: Tenant) -> Tenant:
    session.add(tenant)
    await session.flush()
    await session.refresh(tenant)
    return tenant


async def update_tenant(
    session: AsyncSession, tenant: Tenant, **fields: object
) -> Tenant:
    for key, value in fields.items():
        setattr(tenant, key, value)
    await session.flush()
    return tenant


async def count_users_by_tenant(session: AsyncSession, tenant_id: int) -> int:
    result = await session.execute(
        select(func.count(User.id)).where(User.tenant_id == tenant_id)
    )
    return result.scalar_one()
