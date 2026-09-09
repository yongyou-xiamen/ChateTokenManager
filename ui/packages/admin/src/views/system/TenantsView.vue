<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import {
  Building2,
  Plus,
  Search,
  LoaderCircle,
  Pencil,
  Power,
  PowerOff,
  X,
  Check,
} from 'lucide-vue-next'
import {
  listTenants,
  createTenant,
  updateTenant,
  updateTenantStatus,
  type Tenant,
} from '@aihelms/shared'

const tenants = ref<Tenant[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const keyword = ref('')
const isLoading = ref(false)

const showCreateDialog = ref(false)
const showEditDialog = ref(false)
const editingTenant = ref<Tenant | null>(null)
const saving = ref(false)

const formData = ref({
  name: '',
  slug: '',
  settings: '',
})
const formError = ref('')

const filteredTenants = computed(() => tenants.value)

async function fetchTenants() {
  isLoading.value = true
  try {
    const data = await listTenants(page.value, pageSize.value, keyword.value || undefined)
    tenants.value = data.items
    total.value = data.total
  } finally {
    isLoading.value = false
  }
}

async function handleSearch() {
  page.value = 1
  await fetchTenants()
}

function openCreateDialog() {
  formData.value = { name: '', slug: '', settings: '' }
  formError.value = ''
  showCreateDialog.value = true
}

function openEditDialog(tenant: Tenant) {
  editingTenant.value = tenant
  formData.value = {
    name: tenant.name,
    slug: tenant.slug,
    settings: JSON.stringify(tenant.settings, null, 2),
  }
  formError.value = ''
  showEditDialog.value = true
}

function validateForm(): boolean {
  if (!formData.value.name.trim()) {
    formError.value = '请输入租户名称'
    return false
  }
  if (!formData.value.slug.trim()) {
    formError.value = '请输入租户标识'
    return false
  }
  if (!/^[a-z0-9][a-z0-9-]*$/.test(formData.value.slug)) {
    formError.value = '标识只能包含小写字母、数字和连字符'
    return false
  }
  if (formData.value.settings) {
    try {
      JSON.parse(formData.value.settings)
    } catch {
      formError.value = '设置必须是有效的 JSON'
      return false
    }
  }
  formError.value = ''
  return true
}

async function handleCreate() {
  if (!validateForm()) return
  saving.value = true
  try {
    const settings = formData.value.settings ? JSON.parse(formData.value.settings) : undefined
    await createTenant({
      name: formData.value.name.trim(),
      slug: formData.value.slug.trim(),
      settings,
    })
    showCreateDialog.value = false
    await fetchTenants()
  } catch (e) {
    formError.value = e instanceof Error ? e.message : '创建失败'
  } finally {
    saving.value = false
  }
}

async function handleEdit() {
  if (!editingTenant.value || !validateForm()) return
  saving.value = true
  try {
    const settings = formData.value.settings ? JSON.parse(formData.value.settings) : undefined
    await updateTenant(editingTenant.value.id, {
      name: formData.value.name.trim(),
      slug: formData.value.slug.trim(),
      settings,
    })
    showEditDialog.value = false
    await fetchTenants()
  } catch (e) {
    formError.value = e instanceof Error ? e.message : '更新失败'
  } finally {
    saving.value = false
  }
}

async function toggleStatus(tenant: Tenant) {
  const newStatus = tenant.status === 'active' ? 'suspended' : 'active'
  await updateTenantStatus(tenant.id, newStatus)
  await fetchTenants()
}

onMounted(fetchTenants)
</script>

<template>
  <div class="mx-auto max-w-6xl space-y-6">
    <header class="flex items-center justify-between">
      <div>
        <h1 class="text-xl font-semibold text-slate-950">租户管理</h1>
        <p class="mt-1 text-sm text-slate-500">平台多租户管理与隔离配置</p>
      </div>
      <button
        class="inline-flex h-9 items-center gap-2 rounded-md bg-slate-900 px-4 text-sm font-medium text-white transition-colors hover:bg-slate-700"
        @click="openCreateDialog"
      >
        <Plus class="h-4 w-4" />
        新建租户
      </button>
    </header>

    <section class="overflow-hidden rounded-lg border border-slate-200 bg-white">
      <div class="flex items-center gap-3 border-b border-slate-100 px-5 py-4">
        <Building2 class="h-5 w-5 text-slate-600" />
        <h2 class="text-sm font-semibold text-slate-900">租户列表</h2>
        <div class="ml-auto flex items-center gap-2">
          <div class="relative">
            <Search class="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              v-model="keyword"
              placeholder="搜索租户名称"
              class="h-9 w-56 rounded-md border border-slate-300 pl-8 pr-3 text-sm outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
              @keyup.enter="handleSearch"
            />
          </div>
          <button
            class="inline-flex h-9 items-center gap-1.5 rounded-md border border-slate-300 bg-white px-3 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
            @click="handleSearch"
          >
            搜索
          </button>
        </div>
      </div>

      <div class="relative">
        <div
          v-if="isLoading"
          class="absolute inset-0 z-10 flex items-center justify-center bg-white/60"
        >
          <LoaderCircle class="h-6 w-6 animate-spin text-slate-400" />
        </div>
        <table class="w-full text-sm">
          <thead class="border-b border-slate-100 bg-slate-50/50 text-left text-xs font-medium text-slate-500">
            <tr>
              <th class="px-5 py-3">名称</th>
              <th class="px-5 py-3">标识</th>
              <th class="px-5 py-3">状态</th>
              <th class="px-5 py-3">用户数</th>
              <th class="px-5 py-3">创建时间</th>
              <th class="px-5 py-3 text-right">操作</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr v-if="filteredTenants.length === 0">
              <td colspan="6" class="px-5 py-12 text-center text-slate-400">暂无租户</td>
            </tr>
            <tr
              v-for="tenant in filteredTenants"
              :key="tenant.id"
              class="transition-colors hover:bg-slate-50/50"
            >
              <td class="px-5 py-3 font-medium text-slate-900">{{ tenant.name }}</td>
              <td class="px-5 py-3 text-slate-600">{{ tenant.slug }}</td>
              <td class="px-5 py-3">
                <span
                  class="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium"
                  :class="tenant.status === 'active' ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'"
                >
                  <Check v-if="tenant.status === 'active'" class="h-3 w-3" />
                  <X v-else class="h-3 w-3" />
                  {{ tenant.status === 'active' ? '启用' : '停用' }}
                </span>
              </td>
              <td class="px-5 py-3 text-slate-600">{{ tenant.user_count }}</td>
              <td class="px-5 py-3 text-slate-500">{{ tenant.created_at?.slice(0, 19).replace('T', ' ') }}</td>
              <td class="px-5 py-3">
                <div class="flex items-center justify-end gap-1">
                  <button
                    class="inline-flex h-8 items-center gap-1 rounded-md px-2 text-xs font-medium text-slate-600 transition-colors hover:bg-slate-100"
                    title="编辑"
                    @click="openEditDialog(tenant)"
                  >
                    <Pencil class="h-3.5 w-3.5" />
                    编辑
                  </button>
                  <button
                    v-if="tenant.status === 'active'"
                    class="inline-flex h-8 items-center gap-1 rounded-md px-2 text-xs font-medium text-amber-600 transition-colors hover:bg-amber-50"
                    title="停用"
                    @click="toggleStatus(tenant)"
                  >
                    <PowerOff class="h-3.5 w-3.5" />
                    停用
                  </button>
                  <button
                    v-else
                    class="inline-flex h-8 items-center gap-1 rounded-md px-2 text-xs font-medium text-emerald-600 transition-colors hover:bg-emerald-50"
                    title="启用"
                    @click="toggleStatus(tenant)"
                  >
                    <Power class="h-3.5 w-3.5" />
                    启用
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div
        v-if="total > pageSize"
        class="flex items-center justify-between border-t border-slate-100 px-5 py-3 text-xs text-slate-500"
      >
        <span>共 {{ total }} 条</span>
        <div class="flex items-center gap-2">
          <button
            class="inline-flex h-8 items-center rounded-md border border-slate-300 px-3 font-medium text-slate-600 transition-colors hover:bg-slate-50 disabled:opacity-40"
            :disabled="page <= 1"
            @click="page--; fetchTenants()"
          >
            上一页
          </button>
          <span class="text-slate-600">{{ page }} / {{ Math.ceil(total / pageSize) }}</span>
          <button
            class="inline-flex h-8 items-center rounded-md border border-slate-300 px-3 font-medium text-slate-600 transition-colors hover:bg-slate-50 disabled:opacity-40"
            :disabled="page >= Math.ceil(total / pageSize)"
            @click="page++; fetchTenants()"
          >
            下一页
          </button>
        </div>
      </div>
    </section>

    <!-- 创建/编辑对话框 -->
    <div
      v-if="showCreateDialog || showEditDialog"
      class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4"
      @click.self="showCreateDialog = false; showEditDialog = false"
    >
      <div class="w-full max-w-md rounded-lg bg-white shadow-xl">
        <div class="flex items-center justify-between border-b border-slate-100 px-5 py-4">
          <h3 class="text-sm font-semibold text-slate-900">
            {{ showEditDialog ? '编辑租户' : '新建租户' }}
          </h3>
          <button
            class="text-slate-400 transition-colors hover:text-slate-600"
            @click="showCreateDialog = false; showEditDialog = false"
          >
            <X class="h-4 w-4" />
          </button>
        </div>
        <div class="space-y-4 px-5 py-5">
          <label class="block">
            <span class="mb-1.5 block text-xs font-medium text-slate-600">租户名称</span>
            <input
              v-model="formData.name"
              maxlength="100"
              placeholder="例如：Acme 公司"
              class="h-10 w-full rounded-md border border-slate-300 px-3 text-sm outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
            />
          </label>
          <label class="block">
            <span class="mb-1.5 block text-xs font-medium text-slate-600">租户标识 (slug)</span>
            <input
              v-model="formData.slug"
              maxlength="50"
              placeholder="例如：acme"
              class="h-10 w-full rounded-md border border-slate-300 px-3 text-sm outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
            />
            <span class="mt-1 block text-xs text-slate-400">小写字母、数字、连字符</span>
          </label>
          <label class="block">
            <span class="mb-1.5 block text-xs font-medium text-slate-600">设置 (JSON, 可选)</span>
            <textarea
              v-model="formData.settings"
              rows="4"
              placeholder='{"theme": "blue"}'
              class="w-full rounded-md border border-slate-300 px-3 py-2 font-mono text-xs outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
            />
          </label>
          <p v-if="formError" class="text-xs text-red-600">{{ formError }}</p>
        </div>
        <div class="flex items-center justify-end gap-2 border-t border-slate-100 px-5 py-4">
          <button
            class="inline-flex h-9 items-center rounded-md border border-slate-300 px-4 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
            @click="showCreateDialog = false; showEditDialog = false"
          >
            取消
          </button>
          <button
            class="inline-flex h-9 items-center gap-2 rounded-md bg-slate-900 px-4 text-sm font-medium text-white transition-colors hover:bg-slate-700 disabled:opacity-40"
            :disabled="saving"
            @click="showEditDialog ? handleEdit() : handleCreate()"
          >
            <LoaderCircle v-if="saving" class="h-4 w-4 animate-spin" />
            {{ showEditDialog ? '保存' : '创建' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
