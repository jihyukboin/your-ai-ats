<script setup>
import { nextTick, ref } from 'vue'
import { companyPath } from '../utils/companyPath.js'

const props = defineProps({ initialCompanies: Array, listError: Boolean, activeCompanyId: Number })
const companies = ref(props.initialCompanies)
const failed = ref(props.listError)
const editing = ref(null)
const name = ref('')
const input = ref(null)
const addButton = ref(null)
const busy = ref(false)
const error = ref('')

const itemClasses = 'mb-[2px] flex min-h-[40px] w-full items-center gap-[4px] rounded-[8px] px-[8px] text-[13.5px] font-medium'
const actionClasses = 'min-h-[32px] px-[4px] text-[12px] pointer-coarse:min-h-[44px] pointer-coarse:min-w-[44px]'
const rowActionClasses = 'hover:underline fine-hover:group-[:not(:hover):not(:focus-within)]:opacity-0'


async function edit(id, value = '') {
  editing.value = id
  name.value = value
  error.value = ''
  await nextTick()
  input.value?.focus()
  input.value?.select()
}

function close(restoreFocus = true) {
  editing.value = null
  error.value = ''
  if (restoreFocus) nextTick(() => addButton.value.focus())
}

async function change(method, id) {
  if (busy.value) return
  const value = name.value.trim()
  if (['POST', 'PUT'].includes(method) && !value) {
    error.value = '기업 이름을 입력하세요.'
    return
  }
  busy.value = true
  error.value = ''
  try {
    const url = '/api/companies' + (typeof id === 'number' ? '/' + id : '')
    const writingName = method === 'POST' || method === 'PUT'
    const result = await fetch(url, {
      method,
      ...(writingName && { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: value }) })
    })
    if (!result.ok) throw new Error()
    if (method === 'GET') {
      companies.value = await result.json()
      failed.value = false
    } else if (method === 'DELETE') {
      companies.value = companies.value.filter(company => company.id !== id)
      if (id === props.activeCompanyId) window.location.replace('/')
    } else {
      const company = await result.json()
      companies.value = method === 'POST' ? [company, ...companies.value]
        : companies.value.map(item => item.id === id ? company : item)
      if (method === 'PUT' && id === props.activeCompanyId) {
        const path = companyPath(company)
        if (path !== window.location.pathname) window.location.replace(path)
      }
    }
    close()
  } catch {
    error.value = '요청을 처리할 수 없습니다. 다시 시도해 주세요.'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <section
    class="min-h-0 flex-1 overflow-auto overscroll-contain pt-[20px] text-[12px] text-muted scrollbar-thin
      [&>p]:px-[12px] [&>p]:py-[8px]"
    aria-label="기업 목록"
  >
    <button ref="addButton" :class="itemClasses"
      class="hover:bg-hover hover:text-ink aria-expanded:bg-active aria-expanded:text-ink
        pointer-coarse:min-h-[44px]" :aria-expanded="editing === 'new'" :disabled="busy || failed"
      @mousedown.prevent @click="editing === 'new' ? close() : edit('new')">기업 추가</button>
    <template v-for="row in [{ id: 'new' }, ...companies]" :key="row.id">
      <form v-if="editing === row.id" :class="itemClasses"
        class="border border-line-strong bg-white/3 text-ink focus-within:border-focus/55 focus-within:shadow-[0_0_0_3px_rgb(229_33_46/0.14)]"
        @submit.prevent="change(row.id === 'new' ? 'POST' : 'PUT', row.id)"
        @keydown.esc.stop.prevent="!busy && close()">
        <input :ref="el => { if (el) input = el }" v-model="name"
          class="min-w-0 flex-1 outline-none placeholder:text-subtle pointer-coarse:text-[16px]"
          aria-label="기업 이름" placeholder="기업 이름"
          maxlength="60" autocomplete="off" enterkeyhint="done" :readonly="busy"
          @blur="!busy && !name.trim() && close(false)" />
        <button :class="actionClasses" aria-label="기업 이름 저장" title="저장" :disabled="busy" @mousedown.prevent>↵</button>
      </form>
      <div v-else-if="row.id !== 'new'" :class="itemClasses"
        class="group hover:bg-hover hover:text-ink focus-within:bg-hover focus-within:text-ink
          has-aria-[current=page]:bg-active has-aria-[current=page]:text-ink">
        <a :href="companyPath(row)" :aria-current="row.id === activeCompanyId ? 'page' : undefined"
          class="flex min-h-[40px] min-w-0 flex-1 items-center pointer-coarse:min-h-[44px]" :title="row.name">
          <span class="truncate pointer-coarse:py-[8px] pointer-coarse:wrap-anywhere pointer-coarse:whitespace-normal">{{ row.name }}</span>
        </a>
        <button :class="[actionClasses, rowActionClasses]" :aria-label="row.name + ' 수정'" :disabled="busy"
          @click="edit(row.id, row.name)">수정</button>
        <button :class="[actionClasses, rowActionClasses]" :aria-label="row.name + ' 삭제'" :disabled="busy"
          @click="change('DELETE', row.id)">삭제</button>
      </div>
    </template>
    <p v-if="failed">기업 목록을 불러오지 못했습니다. <button :disabled="busy" @click="change('GET')">다시 시도</button></p>
    <p v-else-if="!companies.length && editing === null">표시할 기업이 없습니다.</p>
    <p v-if="error" class="text-danger" role="alert">{{ error }}</p>
  </section>
</template>
