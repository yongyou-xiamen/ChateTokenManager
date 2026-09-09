from sqlalchemy import select, func, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from models.db import Skill, SkillCategory
from repositories.base import apply_tenant_filter


# ─── Skill ───────────────────────────────────────────────────────────────────


async def create(session: AsyncSession, skill: Skill) -> Skill:
    session.add(skill)
    await session.flush()
    await session.refresh(skill)
    return skill


async def find_by_id(
    session: AsyncSession, skill_id: int, tenant_id: int | None = None
) -> Skill | None:
    stmt = apply_tenant_filter(
        select(Skill).where(Skill.id == skill_id), Skill, tenant_id
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def find_by_skill_id(
    session: AsyncSession, skill_id: str, tenant_id: int | None = None
) -> Skill | None:
    stmt = apply_tenant_filter(
        select(Skill).where(Skill.skill_id == skill_id), Skill, tenant_id
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def find_all(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 50,
    category: str | None = None,
    is_published: bool | None = None,
    is_active: bool | None = None,
    tenant_id: int | None = None,
) -> list[Skill]:
    stmt = apply_tenant_filter(select(Skill), Skill, tenant_id).order_by(
        Skill.id.desc()
    )
    if category:
        stmt = stmt.where(Skill.category == category)
    if is_published is not None:
        stmt = stmt.where(Skill.is_published == is_published)
    if is_active is not None:
        stmt = stmt.where(Skill.is_active == is_active)
    offset = (page - 1) * page_size
    stmt = stmt.limit(page_size).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_all(
    session: AsyncSession,
    category: str | None = None,
    is_published: bool | None = None,
    is_active: bool | None = None,
    tenant_id: int | None = None,
) -> int:
    stmt = apply_tenant_filter(select(func.count(Skill.id)), Skill, tenant_id)
    if category:
        stmt = stmt.where(Skill.category == category)
    if is_published is not None:
        stmt = stmt.where(Skill.is_published == is_published)
    if is_active is not None:
        stmt = stmt.where(Skill.is_active == is_active)
    result = await session.execute(stmt)
    return result.scalar_one()


async def find_by_ids(
    session: AsyncSession, ids: list[int], tenant_id: int | None = None
) -> list[Skill]:
    if not ids:
        return []
    stmt = apply_tenant_filter(select(Skill).where(Skill.id.in_(ids)), Skill, tenant_id)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def delete(session: AsyncSession, skill_id: int) -> bool:
    result = await session.execute(sa_delete(Skill).where(Skill.id == skill_id))
    return result.rowcount > 0


async def increment_install_count(session: AsyncSession, skill_id: int) -> None:
    skill = await find_by_id(session, skill_id)
    if skill:
        skill.install_count = (skill.install_count or 0) + 1


# ─── SkillCategory ──────────────────────────────────────────────────────────


async def list_categories(session: AsyncSession) -> list[SkillCategory]:
    result = await session.execute(
        select(SkillCategory).order_by(SkillCategory.sort_order, SkillCategory.id)
    )
    return list(result.scalars().all())


async def find_category_by_id(
    session: AsyncSession, category_id: int
) -> SkillCategory | None:
    result = await session.execute(
        select(SkillCategory).where(SkillCategory.id == category_id)
    )
    return result.scalar_one_or_none()


async def find_category_by_name(
    session: AsyncSession, name: str
) -> SkillCategory | None:
    result = await session.execute(
        select(SkillCategory).where(SkillCategory.name == name)
    )
    return result.scalar_one_or_none()


async def create_category(
    session: AsyncSession, category: SkillCategory
) -> SkillCategory:
    session.add(category)
    await session.flush()
    await session.refresh(category)
    return category


async def delete_category(session: AsyncSession, category_id: int) -> bool:
    result = await session.execute(
        sa_delete(SkillCategory).where(SkillCategory.id == category_id)
    )
    return result.rowcount > 0
