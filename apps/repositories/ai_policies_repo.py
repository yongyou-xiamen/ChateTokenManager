from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.db import AiPoliciesAudit, AiPoliciesRiskCatalog, AiPoliciesSettings
from repositories.base import apply_tenant_filter


async def create_audit(
    session: AsyncSession, audit: AiPoliciesAudit
) -> AiPoliciesAudit:
    session.add(audit)
    await session.flush()
    await session.refresh(audit)
    return audit


async def find_by_id(
    session: AsyncSession, audit_id: int, tenant_id: int | None = None
) -> AiPoliciesAudit | None:
    stmt = apply_tenant_filter(
        select(AiPoliciesAudit).where(AiPoliciesAudit.id == audit_id),
        AiPoliciesAudit,
        tenant_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def find_by_audit_id(
    session: AsyncSession, audit_id: str, tenant_id: int | None = None
) -> AiPoliciesAudit | None:
    stmt = apply_tenant_filter(
        select(AiPoliciesAudit).where(AiPoliciesAudit.audit_id == audit_id),
        AiPoliciesAudit,
        tenant_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def find_by_ids(
    session: AsyncSession,
    audit_ids: list[int],
    tenant_id: int | None = None,
) -> list[AiPoliciesAudit]:
    if not audit_ids:
        return []
    stmt = apply_tenant_filter(
        select(AiPoliciesAudit).where(AiPoliciesAudit.id.in_(audit_ids)),
        AiPoliciesAudit,
        tenant_id,
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def find_active_by_skill(
    session: AsyncSession, skill_id: int, tenant_id: int | None = None
) -> AiPoliciesAudit | None:
    stmt = (
        apply_tenant_filter(
            select(AiPoliciesAudit).where(
                AiPoliciesAudit.audit_type == "skill",
                AiPoliciesAudit.skill_id == skill_id,
                AiPoliciesAudit.status.in_(["queued", "running"]),
            ),
            AiPoliciesAudit,
            tenant_id,
        )
        .order_by(AiPoliciesAudit.created_at.desc(), AiPoliciesAudit.id.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


def _apply_filters(
    stmt,
    audit_type: str | None = None,
    skill_id: int | None = None,
    status: str | None = None,
    decision: str | None = None,
    q: str | None = None,
    finished_from: datetime | None = None,
    finished_to: datetime | None = None,
    unfinished: bool | None = None,
):
    if audit_type:
        stmt = stmt.where(AiPoliciesAudit.audit_type == audit_type)
    if skill_id:
        stmt = stmt.where(AiPoliciesAudit.skill_id == skill_id)
    if status:
        stmt = stmt.where(AiPoliciesAudit.status == status)
    if decision:
        stmt = stmt.where(AiPoliciesAudit.decision == decision)
    if q:
        stmt = stmt.where(AiPoliciesAudit.skill_name.ilike(f"%{q}%"))
    if unfinished is True:
        stmt = stmt.where(AiPoliciesAudit.finished_at.is_(None))
    elif unfinished is False:
        stmt = stmt.where(AiPoliciesAudit.finished_at.is_not(None))
    if finished_from:
        stmt = stmt.where(AiPoliciesAudit.finished_at >= finished_from)
    if finished_to:
        stmt = stmt.where(AiPoliciesAudit.finished_at <= finished_to)
    return stmt


async def find_all(
    session: AsyncSession,
    page: int,
    page_size: int,
    audit_type: str | None = None,
    skill_id: int | None = None,
    status: str | None = None,
    decision: str | None = None,
    q: str | None = None,
    finished_from: datetime | None = None,
    finished_to: datetime | None = None,
    unfinished: bool | None = None,
    tenant_id: int | None = None,
) -> list[AiPoliciesAudit]:
    stmt = apply_tenant_filter(
        select(AiPoliciesAudit).order_by(
            AiPoliciesAudit.created_at.desc(), AiPoliciesAudit.id.desc()
        ),
        AiPoliciesAudit,
        tenant_id,
    )
    stmt = _apply_filters(
        stmt,
        audit_type,
        skill_id,
        status,
        decision,
        q,
        finished_from,
        finished_to,
        unfinished,
    )
    stmt = stmt.limit(page_size).offset((page - 1) * page_size)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_all(
    session: AsyncSession,
    audit_type: str | None = None,
    skill_id: int | None = None,
    status: str | None = None,
    decision: str | None = None,
    q: str | None = None,
    finished_from: datetime | None = None,
    finished_to: datetime | None = None,
    unfinished: bool | None = None,
    tenant_id: int | None = None,
) -> int:
    stmt = apply_tenant_filter(
        select(func.count(AiPoliciesAudit.id)), AiPoliciesAudit, tenant_id
    )
    stmt = _apply_filters(
        stmt,
        audit_type,
        skill_id,
        status,
        decision,
        q,
        finished_from,
        finished_to,
        unfinished,
    )
    result = await session.execute(stmt)
    return result.scalar_one()


async def list_catalog(session: AsyncSession) -> list[AiPoliciesRiskCatalog]:
    result = await session.execute(
        select(AiPoliciesRiskCatalog).order_by(AiPoliciesRiskCatalog.sort_order)
    )
    return list(result.scalars().all())


async def get_settings(
    session: AsyncSession, tenant_id: int | None = None
) -> AiPoliciesSettings:
    stmt = select(AiPoliciesSettings)
    if tenant_id is not None:
        stmt = stmt.where(AiPoliciesSettings.tenant_id == tenant_id)
    result = await session.execute(stmt.limit(1))
    settings = result.scalar_one_or_none()
    if settings:
        return settings
    settings = AiPoliciesSettings(tenant_id=tenant_id or 1)
    session.add(settings)
    await session.flush()
    await session.refresh(settings)
    return settings
