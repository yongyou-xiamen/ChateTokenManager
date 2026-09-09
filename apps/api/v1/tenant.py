"""租户内 API — 当前租户信息

登录用户查询自己所属租户的信息。租户管理员可更新租户设置。
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_current_user, get_db, require_permission
from exceptions import NotFoundError
from services import tenant_service

router = APIRouter(prefix="/tenant", tags=["租户"])


class UpdateTenantSettingsRequest(BaseModel):
    settings: dict = Field(...)


@router.get("", summary="当前租户信息")
async def get_current_tenant(
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    tenant_id = current_user.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=403, detail="当前身份无租户归属")
    try:
        data = await tenant_service.get_current_tenant(session, tenant_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="租户不存在")
    return {"code": 200, "message": "ok", "data": data}


@router.put("/settings", summary="更新租户设置(租户管理员)")
async def update_tenant_settings(
    req: UpdateTenantSettingsRequest,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("tenant:write")),
):
    tenant_id = current_user.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=403, detail="当前身份无租户归属")
    try:
        data = await tenant_service.update_tenant(
            session, tenant_id, settings=req.settings
        )
    except NotFoundError:
        raise HTTPException(status_code=404, detail="租户不存在")
    return {"code": 200, "message": "租户设置更新成功", "data": data}
