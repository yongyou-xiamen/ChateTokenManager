from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.db import Credential
from repositories.base import apply_tenant_filter


async def create(session: AsyncSession, credential: Credential) -> Credential:
    session.add(credential)
    await session.flush()
    await session.refresh(credential)
    return credential


async def find_by_id(
    session: AsyncSession, credential_id: int, tenant_id: int | None = None
) -> Credential | None:
    stmt = apply_tenant_filter(
        select(Credential).where(Credential.id == credential_id),
        Credential,
        tenant_id,
    ).options(selectinload(Credential.provider), selectinload(Credential.deployments))
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def find_by_name(
    session: AsyncSession,
    credential_name: str,
    provider_id: int | None = None,
    tenant_id: int | None = None,
) -> Credential | None:
    stmt = apply_tenant_filter(
        select(Credential).where(Credential.credential_name == credential_name),
        Credential,
        tenant_id,
    )
    if provider_id is not None:
        stmt = stmt.where(Credential.provider_id == provider_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def find_all(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 50,
    provider_id: int | None = None,
    is_active: bool | None = None,
    tenant_id: int | None = None,
) -> list[Credential]:
    stmt = apply_tenant_filter(select(Credential), Credential, tenant_id)
    stmt = stmt.options(
        selectinload(Credential.provider), selectinload(Credential.deployments)
    ).order_by(Credential.id)
    if provider_id is not None:
        stmt = stmt.where(Credential.provider_id == provider_id)
    if is_active is not None:
        stmt = stmt.where(Credential.is_active == is_active)
    offset = (page - 1) * page_size
    stmt = stmt.limit(page_size).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_all(
    session: AsyncSession,
    provider_id: int | None = None,
    is_active: bool | None = None,
    tenant_id: int | None = None,
) -> int:
    stmt = apply_tenant_filter(select(func.count(Credential.id)), Credential, tenant_id)
    if provider_id is not None:
        stmt = stmt.where(Credential.provider_id == provider_id)
    if is_active is not None:
        stmt = stmt.where(Credential.is_active == is_active)
    result = await session.execute(stmt)
    return result.scalar_one()


async def find_all_active(
    session: AsyncSession, tenant_id: int | None = None
) -> list[Credential]:
    stmt = apply_tenant_filter(
        select(Credential).where(Credential.is_active == True), Credential, tenant_id
    )
    result = await session.execute(stmt.order_by(Credential.id))
    return list(result.scalars().all())


async def find_by_provider(
    session: AsyncSession, provider_id: int, tenant_id: int | None = None
) -> list[Credential]:
    stmt = apply_tenant_filter(
        select(Credential).where(Credential.provider_id == provider_id),
        Credential,
        tenant_id,
    )
    result = await session.execute(stmt.order_by(Credential.id))
    return list(result.scalars().all())
