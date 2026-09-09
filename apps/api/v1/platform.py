"""平台超管 API — 租户管理

仅 is_super_admin 可访问。用于创建/编辑/停用租户、查看跨租户统计。
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_db, require_super_admin
from exceptions import ConflictError, NotFoundError
from services import tenant_service

router = APIRouter(prefix="/platform", tags=["平台管理"])


class CreateTenantRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    slug: str = Field(..., min_length=1, max_length=50, pattern=r"^[a-z0-9][a-z0-9-]*$")
    settings: dict | None = None


class UpdateTenantRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    slug: str | None = Field(
        None, min_length=1, max_length=50, pattern=r"^[a-z0-9][a-z0-9-]*$"
    )
    settings: dict | None = None


class UpdateTenantStatusRequest(BaseModel):
    status: str = Field(..., pattern=r"^(active|suspended)$")


@router.get("/tenants", summary="租户列表")
async def list_tenants(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str = Query("", max_length=50),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_super_admin()),
):
    items, total = await tenant_service.list_tenants(session, page, page_size, keyword)
    return {"code": 200, "message": "ok", "data": {"items": items, "total": total}}


@router.post("/tenants", summary="创建租户")
async def create_tenant(
    req: CreateTenantRequest,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_super_admin()),
):
    try:
        data = await tenant_service.create_tenant(
            session, name=req.name, slug=req.slug, settings=req.settings
        )
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"code": 200, "message": "租户创建成功", "data": data}


@router.get("/tenants/{tenant_id}", summary="租户详情")
async def get_tenant(
    tenant_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_super_admin()),
):
    try:
        data = await tenant_service.get_tenant(session, tenant_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="租户不存在")
    return {"code": 200, "message": "ok", "data": data}


@router.put("/tenants/{tenant_id}", summary="编辑租户")
async def update_tenant(
    tenant_id: int,
    req: UpdateTenantRequest,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_super_admin()),
):
    fields = {k: v for k, v in req.model_dump().items() if v is not None}
    try:
        data = await tenant_service.update_tenant(session, tenant_id, **fields)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="租户不存在")
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"code": 200, "message": "租户更新成功", "data": data}


@router.patch("/tenants/{tenant_id}/status", summary="停用/启用租户")
async def update_tenant_status(
    tenant_id: int,
    req: UpdateTenantStatusRequest,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_super_admin()),
):
    try:
        data = await tenant_service.update_tenant_status(session, tenant_id, req.status)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="租户不存在")
    except ConflictError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"code": 200, "message": "租户状态更新成功", "data": data}
