from sqlalchemy import select, func, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.db import Department, UserDepartment, User
from repositories.base import apply_tenant_filter


async def find_all_active(
    session: AsyncSession, tenant_id: int | None = None
) -> list[Department]:
    stmt = apply_tenant_filter(
        select(Department).where(Department.is_active == True),
        Department,
        tenant_id,
    )
    result = await session.execute(stmt.order_by(Department.sort_order, Department.id))
    return list(result.scalars().all())


async def find_by_id(
    session: AsyncSession, dept_id: int, tenant_id: int | None = None
) -> Department | None:
    stmt = apply_tenant_filter(
        select(Department).where(Department.id == dept_id), Department, tenant_id
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create(session: AsyncSession, dept: Department) -> Department:
    session.add(dept)
    await session.flush()
    await session.refresh(dept)
    return dept


async def count_children(session: AsyncSession, dept_id: int) -> int:
    result = await session.execute(
        select(func.count(Department.id)).where(
            Department.parent_id == dept_id, Department.is_active == True
        )
    )
    return result.scalar_one()


async def count_members(session: AsyncSession, dept_id: int) -> int:
    result = await session.execute(
        select(func.count(UserDepartment.id)).where(
            UserDepartment.department_id == dept_id
        )
    )
    return result.scalar_one()


async def find_members(
    session: AsyncSession, dept_id: int
) -> list[tuple[User, UserDepartment]]:
    result = await session.execute(
        select(User, UserDepartment)
        .join(UserDepartment, UserDepartment.user_id == User.id)
        .where(UserDepartment.department_id == dept_id)
        .order_by(UserDepartment.is_manager.desc(), User.id)
    )
    return list(result.tuples().all())


async def find_membership(
    session: AsyncSession, user_id: int, dept_id: int
) -> UserDepartment | None:
    result = await session.execute(
        select(UserDepartment).where(
            UserDepartment.user_id == user_id, UserDepartment.department_id == dept_id
        )
    )
    return result.scalar_one_or_none()


async def add_member(session: AsyncSession, user_id: int, dept_id: int) -> None:
    session.add(UserDepartment(user_id=user_id, department_id=dept_id))
    await session.flush()


async def remove_member(session: AsyncSession, user_id: int, dept_id: int) -> None:
    await session.execute(
        delete(UserDepartment).where(
            UserDepartment.user_id == user_id, UserDepartment.department_id == dept_id
        )
    )


async def clear_managers(session: AsyncSession, dept_id: int) -> None:
    await session.execute(
        update(UserDepartment)
        .where(UserDepartment.department_id == dept_id)
        .values(is_manager=False)
    )


async def set_managers(
    session: AsyncSession, dept_id: int, user_ids: list[int]
) -> None:
    if user_ids:
        await session.execute(
            update(UserDepartment)
            .where(
                UserDepartment.department_id == dept_id,
                UserDepartment.user_id.in_(user_ids),
            )
            .values(is_manager=True)
        )


async def find_managers(session: AsyncSession, dept_id: int) -> list[User]:
    result = await session.execute(
        select(User)
        .join(UserDepartment, UserDepartment.user_id == User.id)
        .where(
            UserDepartment.department_id == dept_id, UserDepartment.is_manager == True
        )
    )
    return list(result.scalars().all())


async def find_paginated(
    session: AsyncSession,
    page: int,
    page_size: int,
    keyword: str | None = None,
    tenant_id: int | None = None,
) -> tuple[list[Department], int]:
    stmt_count = apply_tenant_filter(
        select(func.count(Department.id)).where(Department.is_active == True),
        Department,
        tenant_id,
    )
    stmt_list = apply_tenant_filter(
        select(Department).where(Department.is_active == True),
        Department,
        tenant_id,
    )
    if keyword:
        pattern = f"%{keyword}%"
        stmt_count = stmt_count.where(Department.name.ilike(pattern))
        stmt_list = stmt_list.where(Department.name.ilike(pattern))
    total = (await session.execute(stmt_count)).scalar_one()
    offset = (page - 1) * page_size
    stmt_list = stmt_list.order_by(Department.sort_order, Department.id)
    stmt_list = stmt_list.limit(page_size).offset(offset)
    result = await session.execute(stmt_list)
    return list(result.scalars().all()), total
