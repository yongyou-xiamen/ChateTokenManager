import { computed } from 'vue'
import { useAuth } from './useAuth'

export function usePermission() {
  const { currentUser } = useAuth()

  const permissions = computed(() => currentUser.value?.permissions ?? [])

  function isSuperAdmin(): boolean {
    return !!currentUser.value?.is_super_admin
  }

  function isTenantAdmin(): boolean {
    return !!currentUser.value?.is_tenant_admin || isSuperAdmin()
  }

  function hasPermission(code: string): boolean {
    if (isSuperAdmin() || isTenantAdmin()) {
      return true
    }
    return permissions.value.includes(code)
  }

  function hasAnyPermission(codes: string[]): boolean {
    return codes.some((code) => hasPermission(code))
  }

  return {
    permissions,
    isSuperAdmin,
    isTenantAdmin,
    hasPermission,
    hasAnyPermission,
  }
}
