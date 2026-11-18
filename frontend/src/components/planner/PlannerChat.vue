<script setup>
import { onMounted, ref } from 'vue'
import { plannerApi } from './api.js'
import RunEvents from './RunEvents.vue'

const example = '내일 14:00부터 15:00까지 Python 이슈 읽기 계획을 짜줘'
const session = ref('')
const runs = ref([])
const message = ref('')
const pending = ref('')
const error = ref('')
const saving = ref(false)
function newSession() {
  session.value = crypto.randomUUID()
  sessionStorage.setItem('portfolio-planner-session', session.value)
  runs.value = []
  message.value = ''
  error.value = ''
}
onMounted(async () => {
  session.value = sessionStorage.getItem('portfolio-planner-session') || ''
  if (!session.value) return newSession()
  const id = session.value
  try {
    const history = await plannerApi('logs/' + id)
    if (id === session.value && !pending.value) runs.value = history.runs
  } catch (e) { if (e.status !== 404) error.value = e.message }
})
async function send() {
  const input = message.value.trim()
  if (!input || pending.value) return
  pending.value = input
  error.value = ''
  message.value = ''
  try {
    const run = await plannerApi('chat', 'POST', { session_id: session.value, message: input })
    runs.value.push({ ...run, message: input })
  } catch (e) {
    error.value = e.message
    message.value = input
  } finally { pending.value = '' }
}
async function save(run) {
  saving.value = true
  error.value = ''
  try {
    const result = await plannerApi('plans', 'POST', run.proposal)
    run.saved = result.overlaps.length ? '저장했습니다. 시간이 겹치는 계획 · ' + result.overlaps.map(x => x.title).join(', ') : '계획을 저장했습니다.'
  } catch (e) { error.value = e.message } finally { saving.value = false }
}
</script>
<template>
  <section>
    <div class="flex items-center justify-between gap-4">
      <h2 class="text-2xl font-semibold">이슈 읽기 계획</h2>
      <button class="text-sm text-muted hover:text-ink" :disabled="!!pending" @click="newSession">새 대화</button>
    </div>
    <p class="mt-2 text-muted">언어와 가능한 시간을 알려 주세요. 열린 GitHub 이슈 중 읽고 정리할 분량을 찾아드립니다.</p>
    <button v-if="!runs.length && !pending" class="mt-5 rounded-lg border border-line-strong px-3 py-2 text-left text-sm hover:bg-hover" @click="message=example">{{ example }}</button>
    <article v-for="run in runs" :key="run.run_id" class="mt-5">
      <p class="ml-auto w-fit max-w-[90%] rounded-xl bg-active px-4 py-3">{{ run.message }}</p>
      <div class="mt-3 rounded-xl border border-line-strong bg-panel p-4">
        <p class="whitespace-pre-line break-words leading-7">{{ run.answer || '응답 기록이 없습니다.' }}</p>
        <a v-if="run.proposal?.url" :href="run.proposal.url" class="mt-2 inline-block text-tint underline" target="_blank" rel="noopener noreferrer">GitHub 이슈 열기</a>
        <ul v-if="run.sources?.length" class="mt-2 space-y-1 text-sm">
          <li v-for="s in run.sources" :key="s.url || s"><a :href="s.url || s" class="text-tint underline break-all" target="_blank" rel="noopener noreferrer">{{ s.name || s.title || s.url || s }}</a><template v-if="s.author"> · Stack Overflow · <a v-if="s.author_url" class="underline" :href="s.author_url" target="_blank" rel="noopener noreferrer">{{ s.author }}</a><span v-else>{{ s.author }}</span> · {{ s.license }}</template></li>
        </ul>
        <div v-if="run.proposal" class="my-3 flex flex-wrap items-center gap-3 border-t border-line pt-3">
          <span>{{ run.proposal.date }} · {{ run.proposal.start_time }} – {{ run.proposal.end_time }}</span>
          <button :disabled="saving || !!run.saved" class="rounded-lg bg-cta px-3 py-2 text-white disabled:opacity-50" @click="save(run)">계획 저장</button>
          <p role="status" v-if="run.saved" class="text-amber-200">{{ run.saved }}</p>
        </div>
        <details class="mt-3 text-sm"><summary class="cursor-pointer font-medium text-muted">실행 과정 · {{ run.events.length }}개 이벤트</summary><RunEvents class="mt-3" :events="run.events" /></details>
      </div>
    </article>
    <p v-if="pending" role="status" class="mt-5 rounded-xl bg-panel p-4">요청 처리 중 · {{ pending }}</p>
    <form class="mt-5 flex items-end gap-2 rounded-xl border border-line-strong p-2 focus-within:border-tint" @submit.prevent="send">
      <textarea v-model="message" aria-label="플래너에게 요청" placeholder="날짜, 시간, 프로그래밍 언어를 입력하세요" rows="2" maxlength="4000" required class="min-w-0 flex-1 resize-y p-2 outline-none" @keydown.enter.exact="event => { if (!event.isComposing) { event.preventDefault(); send() } }"></textarea>
      <button class="rounded-lg bg-cta px-4 py-2 text-white disabled:opacity-50" :disabled="!!pending || !message.trim()">보내기</button>
    </form>
    <p v-if="error" role="alert" class="mt-3 text-danger">{{ error }}</p>
  </section>
</template>
