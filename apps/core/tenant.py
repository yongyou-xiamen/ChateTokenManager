"""多租户上下文中间件

解析 JWT 注入 tenant 上下文到 request.state，供后续中间件（AuditLog）和路由使用。
- 公开端点跳过
- token 缺失或无效时不阻断请求（返回 None），由路由层 Depends(get_current_user) 决定是否 401
"""

import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from core.deps import get_current_user_optional

logger = logging.getLogger(__name__)

PUBLIC_PATHS = {
    "/api/health",
    "/api/v1/auth/login",
    "/api/v1/config/public",
    "/api/v1/ping",
}


class TenantContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        user = await get_current_user_optional(request)
        if user:
            request.state.current_user = user
            request.state.tenant_id = user.get("tenant_id")
            request.state.is_super_admin = user.get("is_super_admin", False)
        return await call_next(request)
