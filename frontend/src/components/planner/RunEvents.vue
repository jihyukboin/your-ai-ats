<script setup>
defineProps({ events: { type: Array, default: () => [] } })
const kinds = { stage_start: '단계 시작', stage_end: '단계 완료', tool_request: '도구 호출', tool_response: '도구 응답', replan: '재계획', plan: '작업 계획', decision: '판단', chat_started: '요청 접수', chat_completed: '응답 완료' }
const stages = { analyze: '요청 분석', plan: '계획 수립', execute: '도구 실행', judge: '제약 판단', respond: '답변 작성', chat: '대화' }
</script>
<template>
  <ol class="space-y-1 pl-1" aria-label="순서별 실행 기록">
    <li v-for="(event, index) in events" :key="event.seq ?? index" class="border-l-2 border-line-strong pl-3 py-1 text-sm" :class="{'border-amber-400 text-amber-300':event.type === 'replan'}">
      <details>
        <summary class="cursor-pointer break-words">
          <span class="text-muted">{{ index + 1 }}.</span> {{ kinds[event.type] || event.type }}
          {{ stages[event.stage] || event.stage }} {{ event.data?.tool || '' }}
          <span v-if="event.data?.duration_ms != null"> · {{ event.data.duration_ms }} ms</span>
          <span v-if="event.data?.reason" class="text-muted"> · {{ event.data.reason }}</span>
        </summary>
        <pre class="mt-2 overflow-x-auto whitespace-pre-wrap break-all text-xs text-muted">{{ JSON.stringify(event.data, null, 2) }}</pre>
      </details>
    </li>
  </ol>
</template>
