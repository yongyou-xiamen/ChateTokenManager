import { computed, ref } from 'vue'
import { getBranding } from '../api/branding'
import type { BrandingInfo } from '../types/branding'

const branding = ref<BrandingInfo | null>(null)
const loading = ref(false)
const logoObjectUrl = ref<string | null>(null)
const faviconObjectUrl = ref<string | null>(null)
const squareLogoObjectUrl = ref<string | null>(null)

function getToken(): string | null {
  return localStorage.getItem('aihelms_token')
}

async function fetchAssetBlobUrl(path: string): Promise<string | null> {
  const token = getToken()
  if (!token) return null
  try {
    const res = await fetch(`/api/v1/branding/${path}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    if (!res.ok) return null
    const blob = await res.blob()
    return URL.createObjectURL(blob)
  } catch {
    return null
  }
}

function revokeAndSet(slot: { value: string | null }, url: string | null): void {
  if (slot.value) URL.revokeObjectURL(slot.value)
  slot.value = url
}

export function useBranding() {
  const logoUrl = computed(() => logoObjectUrl.value)
  const faviconUrl = computed(() => faviconObjectUrl.value)
  const squareLogoUrl = computed(() => squareLogoObjectUrl.value ?? faviconObjectUrl.value)

  async function refresh(): Promise<void> {
    loading.value = true
    try {
      branding.value = await getBranding()
      const info = branding.value
      revokeAndSet(logoObjectUrl, info?.has_logo ? await fetchAssetBlobUrl('logo') : null)
      revokeAndSet(faviconObjectUrl, info?.has_favicon ? await fetchAssetBlobUrl('favicon') : null)
      revokeAndSet(
        squareLogoObjectUrl,
        info?.has_square_logo ? await fetchAssetBlobUrl('square-logo') : null,
      )
    } catch {
      branding.value = null
    } finally {
      loading.value = false
    }
  }

  function applyToDocument(): void {
    document.title = branding.value?.platform_name || 'ChateToken'
    const existing = document.querySelector<HTMLLinkElement>("link[rel='icon']")
    const link = existing ?? document.createElement('link')
    link.rel = 'icon'
    link.href = faviconUrl.value ?? '/favicon.ico'
    if (!existing) document.head.appendChild(link)
  }

  return { branding, loading, logoUrl, squareLogoUrl, faviconUrl, refresh, applyToDocument }
}
