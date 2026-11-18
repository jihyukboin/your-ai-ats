<script setup>
import { onMounted, ref } from 'vue'
import { plannerApi } from './api.js'

const plans = ref([])
const editing = ref(null)
const info = ref('')
const busy = ref(false)
const ready = ref(false)
const error = ref('')
async function load() {
  plans.value = await plannerApi('plans')
  ready.value = true
}
async function act(action) {
  busy.value = true
  error.value = ''
  info.value = ''
  try { await action() } catch (e) { error.value = e.message } finally { busy.value = false }
}
function save() {
  return act(async () => {
    const { id, title, date, start_time, end_time, notes, url } = editing.value
    const result = await plannerApi('plans/' + id, 'PUT', { title, date, start_time, end_time, notes, url })
    editing.value = null
    info.value = result.overlaps.length ? '수정했습니다. 겹치는 계획 · ' + result.overlaps.map(p => p.title).join(', ') : '계획을 수정했습니다.'
    await load()
  })
}
function remove(plan) {
  if (!window.confirm('이 계획을 삭제할까요?')) return
  return act(async () => {
    await plannerApi('plans/' + plan.id, 'DELETE')
    editing.value = null
    await load()
    info.value = '계획을 삭제했습니다.'
  })
}
onMounted(() => act(load))
</script>
<template>
  <section>
    <h2 class="text-2xl font-semibold">저장한 계획</h2>
    <p v-if="error" role="alert">{{ error }} <button class="underline" @click="act(load)">다시 조회</button></p>
    <p v-if="info" role="status" class="mt-3 text-amber-200">{{ info }}</p>
    <p v-if="ready && !plans.length" class="mt-4 text-muted">저장한 계획이 없습니다. 대화에서 추천받은 일정을 저장해 주세요.</p>
    <article v-for="plan in plans" :key="plan.id" class="my-4 rounded-xl border border-line-strong bg-panel p-4">
      <form v-if="editing?.id === plan.id" class="grid gap-3" @submit.prevent="save">
        <label>제목<input v-model="editing.title" required class="edit-input"></label>
        <div class="flex flex-wrap gap-3">
          <label>날짜<input v-model="editing.date" type="date" required class="edit-input"></label>
          <label>시작<input v-model="editing.start_time" type="time" required class="edit-input"></label>
          <label>종료<input v-model="editing.end_time" type="time" required class="edit-input"></label>
        </div>
        <label>메모<textarea v-model="editing.notes" class="edit-input"></textarea></label>
        <div class="flex gap-4"><button class="text-tint" :disabled="busy">변경 저장</button><button type="button" @click="editing=null">취소</button></div>
      </form>
      <template v-else>
        <h3 class="font-semibold break-words">{{ plan.title }}</h3>
        <p class="my-2">{{ plan.date }} · {{ plan.start_time }} – {{ plan.end_time }}</p>
        <p class="whitespace-pre-wrap text-muted">{{ plan.notes }}</p>
        <a v-if="plan.url" class="text-tint underline" :href="plan.url" target="_blank" rel="noopener noreferrer">원본 이슈</a>
        <p class="mt-2 text-xs text-muted">생성 {{ new Date(plan.created_at).toLocaleString('ko-KR') }}</p>
        <div class="mt-3 flex gap-4 text-sm"><button :disabled="busy" @click="act(async () => { editing = await plannerApi('plans/' + plan.id) })">수정</button><button :disabled="busy" class="text-danger" @click="remove(plan)">삭제</button></div>
      </template>
    </article>
  </section>
</template>
