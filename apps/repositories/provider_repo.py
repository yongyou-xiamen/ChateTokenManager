from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.db import Provider
from repositories.base import apply_tenant_filter


async def create(session: AsyncSession, provider: Provider) -> Provider:
    session.add(provider)
    await session.flush()
    await session.refresh(provider)
    return provider


async def find_by_id(
    session: AsyncSession, provider_id: int, tenant_id: int | None = None
) -> Provider | None:
    stmt = apply_tenant_filter(
        select(Provider).where(Provider.id == provider_id), Provider, tenant_id
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def find_all(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 50,
    is_active: bool | None = None,
    tenant_id: int | None = None,
) -> list[Provider]:
    stmt = apply_tenant_filter(select(Provider), Provider, tenant_id).order_by(
        Provider.id
    )
    if is_active is not None:
        stmt = stmt.where(Provider.is_active == is_active)
    offset = (page - 1) * page_size
    stmt = stmt.limit(page_size).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_all(
    session: AsyncSession,
    is_active: bool | None = None,
    tenant_id: int | None = None,
) -> int:
    stmt = apply_tenant_filter(select(func.count(Provider.id)), Provider, tenant_id)
    if is_active is not None:
        stmt = stmt.where(Provider.is_active == is_active)
    result = await session.execute(stmt)
    return result.scalar_one()


async def find_all_active(
    session: AsyncSession, tenant_id: int | None = None
) -> list[Provider]:
    stmt = apply_tenant_filter(
        select(Provider).where(Provider.is_active == True), Provider, tenant_id
    )
    result = await session.execute(stmt.order_by(Provider.id))
    return list(result.scalars().all())
