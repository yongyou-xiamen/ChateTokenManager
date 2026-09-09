import { request } from './request'
import type { Tenant, CreateTenantParams, UpdateTenantParams } from '../types/tenant'

export function listTenants(
  page: number,
  pageSize: number,
  keyword?: string,
): Promise<{ items: Tenant[]; total: number }> {
  return request<{ items: Tenant[]; total: number }>('/api/v1/platform/tenants', {
    params: { page, page_size: pageSize, keyword },
  })
}

export function getTenant(id: number): Promise<Tenant> {
  return request<Tenant>(`/api/v1/platform/tenants/${id}`)
}

export function createTenant(params: CreateTenantParams): Promise<Tenant> {
  return request<Tenant>('/api/v1/platform/tenants', { method: 'POST', body: params })
}

export function updateTenant(id: number, params: UpdateTenantParams): Promise<Tenant> {
  return request<Tenant>(`/api/v1/platform/tenants/${id}`, { method: 'PUT', body: params })
}

export function updateTenantStatus(id: number, status: 'active' | 'suspended'): Promise<Tenant> {
  return request<Tenant>(`/api/v1/platform/tenants/${id}/status`, {
    method: 'PATCH',
    body: { status },
  })
}

export function getCurrentTenant(): Promise<Tenant> {
  return request<Tenant>('/api/v1/tenant')
}

export function updateCurrentTenantSettings(settings: Record<string, unknown>): Promise<Tenant> {
  return request<Tenant>('/api/v1/tenant/settings', { method: 'PUT', body: { settings } })
}
