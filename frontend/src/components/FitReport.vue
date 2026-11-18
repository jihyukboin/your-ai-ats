<script setup>
import { computed } from 'vue'
import { fitReport } from '../utils/fitReport.js'
import AgentReply from './AgentReply.vue'

const props = defineProps({
  message: { type: Object, required: true },
  companyName: { type: String, default: '' },
  userName: { type: String, default: '' },
})

// 평가 결과를 보고서 본문으로 만들어 1단계 답변과 같은 화면(AgentReply)으로 보여줍니다.
const report = computed(() => {
  const run = props.message.run
  const report = run?.result
    ? fitReport(run.result, { company: props.companyName, user: props.userName, role: run.role })
    : { text: '', sources: [] }
  return { ...props.message, ...report, error: props.message.error || run?.error }
})
</script>

<template>
  <AgentReply :message="report" />
</template>
