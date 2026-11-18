<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import { analyzeCompany, restoreRuns } from './companyAnalysis.js'
import { evaluateFit, restoreFits } from './fitAnalysis.js'
import { restoreLetters, writeLetter } from './coverLetter.js'
import ChatComposer from './ChatComposer.vue'
import ChatReply from './ChatReply.vue'

const props = defineProps({
  companyId: { type: Number, required: true },
  companyName: { type: String, required: true },
  userName: { type: String, required: true },
})
const emit = defineEmits(['complete'])

const root = ref(null)
const composer = ref(null)
const messages = ref([])
const busy = ref(true)
const role = ref('')
const historyError = ref('')
onMounted(async () => {
  try {
    const restored = []
    const [analyzed, fitted, written] = await Promise.all([restoreRuns(props.companyId, restored),
      restoreFits(props.companyId, restored), restoreLetters(props.companyId, restored)])
    // 1~3단계 기록을 시작 시각 순으로 합칩니다.
    messages.value = restored.map((message, order) => ({ message, order }))
      .sort((a, b) => (a.message.started ?? '').localeCompare(b.message.started ?? '') || a.order - b.order)
      .map(({ message }) => message)
    if (analyzed) emit('complete', 0)
    if (analyzed && fitted) emit('complete', 1)
    if (analyzed && fitted && written) emit('complete', 2)
  } catch {
    historyError.value = '분석 기록을 불러오지 못했습니다.'
  } finally {
    busy.value = false
  }
})
const started = computed(() => messages.value.length > 0)
let pendingStep = null

// 사용자가 위로 스크롤해 읽는 중이면 자동 스크롤하지 않습니다.
function scrollToEnd(force = false) {
  const scroller = root.value?.parentElement
  if (!scroller) return
  const nearBottom = scroller.scrollHeight - scroller.scrollTop - scroller.clientHeight < 160
  if (force || nearBottom) scroller.scrollTo({ top: scroller.scrollHeight, behavior: force ? 'smooth' : 'auto' })
}

function send(prompt, step = null) {
  if (busy.value) return
  pendingStep = step
  composer.value.send(prompt)
}

// 2·3단계는 각 단계 API로, 그 외 질문(직접 입력 포함)은 1단계 기업/직무 분석 API로 보냅니다.
async function ask(text) {
  const step = pendingStep === 1 || pendingStep === 2 ? pendingStep : 0
  const jobRole = role.value.trim()
  pendingStep = null
  busy.value = true
  messages.value.push({ id: messages.value.length, role: 'user', text: step === 0 && jobRole ? `${text}\n지원 직무 · ${jobRole}` : text })
  messages.value.push(step === 1
    ? { id: messages.value.length, role: 'assistant', kind: 'fit', stages: [], run: null, phase: 'thinking' }
    : { id: messages.value.length, role: 'assistant', stages: [], text: '', sources: [], phase: 'thinking' })
  const reply = messages.value.at(-1)
  await nextTick()
  scrollToEnd(true)
  try {
    if (step === 0) await analyzeCompany(props.companyId, jobRole, text, reply)
    else if (step === 1) await evaluateFit(props.companyId, reply)
    else await writeLetter(props.companyId, text, reply)
    if (reply.phase === 'done') emit('complete', step)
  } catch (error) {
    reply.phase = 'failed'
    reply.error = error.message
  } finally {
    busy.value = false
  }
}

defineExpose({ send })
</script>

<template>
  <div
    ref="root"
    class="flex w-full flex-1 flex-col items-center"
    :class="!started && 'justify-center pb-[10dvh] short:pb-0'"
  >
    <p v-if="historyError" role="alert">{{ historyError }}</p>
    <h1 v-if="!started" class="mb-[32px] px-[24px] text-center text-[32px]/[1.4] font-[550] tracking-[-1px]
      max-sidebar:text-[27px] short:mb-[12px]">
      <span class="inline-block bg-[linear-gradient(90deg,var(--color-tint),#a78bfa_22%,#f472b6_45%,var(--color-ink)_70%)]
        bg-size-[220%_100%] bg-left bg-clip-text text-transparent motion-safe:animate-greet">
        궁금한 것을 물어보세요
      </span>
    </h1>

    <ol v-else class="flex w-full max-w-[816px] flex-1 flex-col gap-[32px] px-[36px] pt-[32px] pb-[24px] max-[768px]:px-[18px]"
      aria-label="대화" aria-live="polite">
      <li v-for="message in messages" :key="message.id">
        <div v-if="message.role === 'user'" class="flex justify-end motion-safe:animate-rise">
          <p class="max-w-[78%] rounded-[22px] rounded-br-[8px] bg-white/8 px-[18px] py-[11px] text-[15px]/[1.65] whitespace-pre-wrap">
            {{ message.text }}
          </p>
        </div>
        <ChatReply v-else :message="message" :company-name="companyName" :user-name="userName" />
      </li>
    </ol>

    <label class="my-2 text-sm text-muted">지원 직무
      <input v-model="role" maxlength="100" placeholder="예: 응용SW엔지니어링" class="edit-input" :disabled="busy" />
    </label>
    <div
      class="flex w-full justify-center"
      :class="started
        ? 'sticky bottom-0 bg-linear-to-t from-bg from-65% to-transparent pt-[24px]'
        : 'motion-safe:animate-rise motion-safe:[animation-delay:250ms] motion-safe:[animation-duration:0.8s]'"
    >
      <ChatComposer ref="composer" :busy="busy" @submit="ask" />
    </div>
  </div>
</template>
