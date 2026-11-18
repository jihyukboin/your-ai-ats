<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  stages: { type: Array, required: true },
  phase: { type: String, required: true },
})

const FIELD_LABELS = {
  corpNm: '회사명', corp_name: '회사명', enpRprFnm: '대표자', ceo_nm: '대표자', enpEstbDt: '설립일', est_dt: '설립일',
  crno: '법인등록번호', corp_code: '고유번호', induty_code: '업종코드', hm_url: '홈페이지', report: '최근 공시',
  filed: '공시일', url: '공시 원문', basDt: '기준일',
}
const STATUS_TEXT = { done: '완료', empty: '자료 없음', failed: '실패', running: '진행 중', interrupted: '중단됨' }
const PHASE_TEXT = { done: '분석 완료', partial: '일부 완료', failed: '분석 실패', interrupted: '중단됨', snapshot: '저장된 진행 기록' }

const running = computed(() => props.phase === 'thinking')
const open = ref(running.value)
watch(running, value => (open.value = value))

const current = computed(() => props.stages.findLast(stage => stage.status === 'running') ?? props.stages.at(-1))

function duration(start, end) {
  const ms = Date.parse(end) - Date.parse(start)
  if (!Number.isFinite(ms) || ms < 0) return ''
  const seconds = ms / 1000
  return seconds < 60 ? `${seconds.toFixed(1)}초` : `${Math.floor(seconds / 60)}분 ${Math.round(seconds % 60)}초`
}

const elapsed = computed(() => {
  const start = props.stages.find(stage => stage.started)?.started
  const end = props.stages.findLast(stage => stage.ended)?.ended
  return start && end ? duration(start, end) : ''
})

const issues = computed(() => {
  const count = status => props.stages.filter(stage => stage.status === status).length
  return [count('empty') && `자료 없음 ${count('empty')}`, count('failed') && `실패 ${count('failed')}`].filter(Boolean)
})

function domain(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return ''
  }
}

function facts(row) {
  return Object.entries(row).filter(([, value]) => value).map(([key, value]) => {
    const text = String(value)
    const href = /^https?:\/\//.test(text) ? text : key === 'hm_url' ? `https://${text}` : null
    return { key, label: FIELD_LABELS[key] ?? key, href, text: href ? domain(href) || text : text.replace(/^(\d{4})(\d{2})(\d{2})$/, '$1.$2.$3') }
  })
}
</script>

<template>
  <div class="rounded-[16px] bg-white/[0.035] shadow-[inset_0_0_0_1px_var(--color-line)]">
    <button
      class="flex w-full items-center gap-[10px] rounded-[16px] px-[14px] py-[11px] text-left hover:bg-hover"
      type="button"
      :aria-expanded="open"
      @click="open = !open"
    >
      <span v-if="running" class="size-[14px] shrink-0 rounded-full border-2 border-line-strong border-t-tint motion-safe:animate-spin"></span>
      <svg v-else class="size-[16px] shrink-0 fill-none stroke-current stroke-2 text-muted" viewBox="0 0 24 24" aria-hidden="true"
        stroke-linecap="round" stroke-linejoin="round">
        <path d="M4 6h16M4 12h10M4 18h6" />
      </svg>
      <span v-if="running" class="min-w-0 flex-1 truncate bg-[linear-gradient(90deg,var(--color-muted)_30%,var(--color-ink)_50%,var(--color-muted)_70%)]
        bg-size-[200%_100%] bg-clip-text text-[14px] font-medium text-transparent motion-safe:animate-shimmer">
        {{ current ? `${current.label} 중…` : '분석 준비 중…' }}
      </span>
      <span v-else class="flex min-w-0 flex-1 items-baseline gap-[8px] text-[14px]">
        <span class="font-medium" :class="['failed', 'partial'].includes(phase) ? 'text-danger' : 'text-ink'">{{ PHASE_TEXT[phase] ?? '분석 완료' }}</span>
        <span class="truncate text-[13px] text-subtle">
          {{ [`${stages.length}단계`, elapsed, ...issues].filter(Boolean).join(' · ') }}
        </span>
      </span>
      <svg class="size-[16px] shrink-0 fill-none stroke-current stroke-2 text-subtle transition-transform duration-300"
        :class="open && 'rotate-180'" viewBox="0 0 24 24" aria-hidden="true" stroke-linecap="round" stroke-linejoin="round">
        <path d="m6 9 6 6 6-6" />
      </svg>
    </button>

    <div class="grid transition-[grid-template-rows] duration-300 ease-out" :class="open ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]'">
      <div class="overflow-hidden" :inert="!open">
        <ol class="px-[14px] pt-[4px] pb-[14px]">
          <li v-for="(stage, index) in stages" :key="stage.label" class="relative flex gap-[12px] pb-[14px] last:pb-0 motion-safe:animate-rise">
            <span v-if="index < stages.length - 1" class="absolute top-[22px] bottom-[2px] left-[8.5px] w-px bg-line-strong" aria-hidden="true"></span>
            <span class="relative mt-[2px] grid size-[18px] shrink-0 place-items-center rounded-full"
              :class="{
                'bg-tint/18 text-tint': stage.status === 'done',
                'bg-white/8 text-subtle': stage.status === 'empty',
                'bg-danger/18 text-danger': stage.status === 'failed',
              }">
              <span v-if="stage.status === 'running'" class="size-[14px] rounded-full border-2 border-line-strong border-t-tint motion-safe:animate-spin"></span>
              <svg v-else class="size-[11px] fill-none stroke-current stroke-[3]" viewBox="0 0 24 24" aria-hidden="true"
                stroke-linecap="round" stroke-linejoin="round">
                <path v-if="stage.status === 'done'" d="m5 12.5 4.5 4.5L19 7.5" />
                <path v-else-if="stage.status === 'failed'" d="M7 7l10 10M17 7 7 17" />
                <path v-else d="M6 12h12" />
              </svg>
            </span>

            <div class="min-w-0 flex-1">
              <div class="flex items-baseline gap-[8px]">
                <span class="text-[14px]" :class="stage.status === 'empty' ? 'text-muted' : 'text-ink'">{{ stage.label }}</span>
                <span v-if="stage.status !== 'done'" class="text-[12px]"
                  :class="stage.status === 'failed' ? 'text-danger' : 'text-subtle'">{{ STATUS_TEXT[stage.status] }}</span>
                <span class="ml-auto shrink-0 text-[12px] text-subtle tabular-nums">{{ duration(stage.started, stage.ended) }}</span>
              </div>
              <p v-if="stage.reason" class="mt-[2px] text-[12.5px]/[1.55] text-muted">{{ stage.reason }}</p>
              <a v-if="stage.source" :href="stage.source" target="_blank" rel="noreferrer"
                class="mt-[4px] inline-block text-[12px] text-subtle hover:text-tint">{{ domain(stage.source) }}</a>

              <dl v-for="(row, rowIndex) in stage.rows ?? []" :key="rowIndex"
                class="mt-[8px] grid grid-cols-[auto_1fr] gap-x-[14px] gap-y-[4px] rounded-[10px] bg-white/4 px-[12px] py-[9px] text-[12.5px]">
                <template v-for="fact in facts(row)" :key="fact.key">
                  <dt class="text-subtle">{{ fact.label }}</dt>
                  <dd class="min-w-0 truncate text-ink/85">
                    <a v-if="fact.href" :href="fact.href" target="_blank" rel="noreferrer" class="text-tint hover:underline">{{ fact.text }}</a>
                    <template v-else>{{ fact.text }}</template>
                  </dd>
                </template>
              </dl>
            </div>
          </li>
        </ol>
      </div>
    </div>
  </div>
</template>
