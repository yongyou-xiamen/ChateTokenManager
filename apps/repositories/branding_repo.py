from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.db import Branding


async def get(session: AsyncSession, tenant_id: int | None = None) -> Branding:
    stmt = select(Branding)
    if tenant_id is not None:
        stmt = stmt.where(Branding.tenant_id == tenant_id)
    result = await session.execute(stmt.limit(1))
    row = result.scalar_one_or_none()
    if row is None:
        row = Branding(tenant_id=tenant_id or 1, platform_name="AIHelms")
        session.add(row)
        await session.flush()
    return row


async def update(
    session: AsyncSession, tenant_id: int | None = None, **fields: object
) -> Branding:
    row = await get(session, tenant_id=tenant_id)
    for key, value in fields.items():
        setattr(row, key, value)
    await session.flush()
    return row
