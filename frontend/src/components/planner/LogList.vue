<script setup>
import { onMounted, ref } from 'vue'
import { plannerApi } from './api.js'
import RunEvents from './RunEvents.vue'

const logs = ref([])
const selected = ref(null)
const error = ref('')
const ready = ref(false)
async function action(work) {
  error.value = ''
  try { await work() } catch (e) { error.value = e.message }
}
async function load() {
  logs.value = await plannerApi('logs')
  ready.value = true
}
function open(session) {
  return action(async () => { selected.value = await plannerApi('logs/' + session) })
}
function remove(session) {
  if (!window.confirm('이 세션의 실행 로그를 삭제할까요?')) return
  return action(async () => { await plannerApi('logs/' + session, 'DELETE'); selected.value = null; await load() })
}
onMounted(() => action(load))
</script>
<template>
  <section>
    <h2 class="text-2xl font-semibold">실행 로그</h2>
    <p v-if="error" role="alert" class="text-danger">{{ error }}</p>
    <p v-if="ready && !logs.length" class="mt-4 text-muted">기록된 대화가 없습니다.</p>
    <article v-for="l in logs" :key="l.session_id" class="mt-4 rounded-xl border border-line-strong bg-panel p-4">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <button class="break-all text-left hover:underline" @click="open(l.session_id)">{{ l.session_id }}<span class="mt-1 block text-xs text-muted">대화 {{ l.run_count }}건 · 이벤트 {{ l.event_count }}개</span></button>
        <button class="text-sm text-danger" @click="remove(l.session_id)">로그 삭제</button>
      </div>
      <div v-if="selected?.session_id === l.session_id" v-for="run in selected?.runs" :key="run.run_id" class="mt-4 border-t border-line pt-4">
        <h3 class="mb-2 font-semibold">{{ run.message }}</h3><RunEvents :events="run.events" />
      </div>
    </article>
  </section>
</template>
