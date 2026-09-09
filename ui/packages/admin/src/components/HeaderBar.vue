<script setup lang="ts">
import { BookOpen, Menu } from 'lucide-vue-next'
import { useAuth, useBranding } from '@aihelms/shared'

const { currentUser, logout } = useAuth()
const { branding } = useBranding()
const emit = defineEmits<{ toggleSidebar: [] }>()

function handleLogout(): void {
  logout()
}
</script>

<template>
  <header class="flex h-14 items-center justify-between gap-2 border-b border-slate-200/60 bg-white/70 px-3 backdrop-blur-lg sm:px-6">
    <div class="flex min-w-0 items-center gap-2">
      <button
        class="flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-slate-600 transition-colors hover:bg-slate-100 md:hidden"
        type="button"
        title="打开导航"
        aria-label="打开导航"
        @click="emit('toggleSidebar')"
      >
        <Menu class="h-5 w-5" />
      </button>
      <div class="hidden min-w-0 truncate text-sm font-medium text-slate-700 sm:block">
        {{ branding?.platform_name || 'ChateToken' }} 管理后台
      </div>
    </div>
    <div class="flex items-center gap-2 sm:gap-4">
      <a
        href="/docs/"
        target="_blank"
        rel="noopener noreferrer"
        class="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm text-slate-600 transition-colors hover:bg-slate-100/80"
        title="查看文档"
      >
        <BookOpen class="h-4 w-4" />
        <span class="hidden sm:inline">文档</span>
      </a>
      <span class="hidden text-sm text-slate-600 sm:inline">{{ currentUser?.username }}</span>
      <button
        class="rounded-lg px-3 py-1.5 text-sm text-slate-600 transition-colors hover:bg-slate-100/80"
        @click="handleLogout"
      >
        退出
      </button>
    </div>
  </header>
</template>
