export interface Tenant {
  id: number
  name: string
  slug: string
  status: 'active' | 'suspended'
  settings: Record<string, unknown>
  user_count: number
  created_at: string
  updated_at: string
}

export interface CreateTenantParams {
  name: string
  slug: string
  settings?: Record<string, unknown>
}

export interface UpdateTenantParams {
  name?: string
  slug?: string
  settings?: Record<string, unknown>
}
