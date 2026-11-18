<script setup>
import { nextTick, onMounted, onUnmounted, ref } from 'vue'

defineProps({ busy: Boolean })
const emit = defineEmits(['submit'])

const prompt = ref('')
const input = ref(null)
const form = ref(null)
const typing = ref(false)
let typingRun = 0

function resizeInput() {
  const textarea = input.value
  textarea.style.height = '30px'
  textarea.style.height = `${textarea.scrollHeight}px`
}

let observer
onMounted(() => {
  let width
  observer = new ResizeObserver(([entry]) => {
    if (entry.contentRect.width === width) return
    width = entry.contentRect.width
    resizeInput()
  })
  observer.observe(form.value)
})
onUnmounted(() => {
  observer?.disconnect()
  typingRun++
})

function submitOnEnter(event) {
  if (event.shiftKey || event.isComposing) return
  event.preventDefault()
  form.value.requestSubmit()
}

async function submit() {
  const text = prompt.value.trim()
  if (!text || typing.value) return
  emit('submit', text)
  prompt.value = ''
  await nextTick()
  resizeInput()
}

async function reset() {
  prompt.value = ''
  await nextTick()
  resizeInput()
  input.value.focus()
}

function focus() {
  input.value.focus()
}

const wait = ms => new Promise(resolve => setTimeout(resolve, ms))

// 프롬프트를 한 글자씩 입력하는 연출 후 자동으로 전송합니다.
async function send(text) {
  const run = ++typingRun
  const chars = Array.from(text)
  const instant = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  typing.value = true
  prompt.value = instant ? text : ''
  for (let index = 0; !instant && index < chars.length; index += 2) {
    await wait(18)
    if (run !== typingRun) return
    prompt.value += chars.slice(index, index + 2).join('')
    await nextTick()
    resizeInput()
  }
  await nextTick()
  resizeInput()
  await wait(instant ? 0 : 380)
  if (run !== typingRun) return
  typing.value = false
  form.value.requestSubmit()
}

defineExpose({ reset, focus, send })
</script>

<template>
  <div class="isolate w-full max-w-[816px] px-[24px] pb-[max(20px,env(safe-area-inset-bottom))] max-[768px]:px-[12px]">
    <form
      ref="form"
      class="composer-glow cursor-text rounded-[28px] border border-line-strong bg-panel px-[13px] pt-[15px] pb-[9px]
        shadow-[0_10px_36px_rgb(0_0_0/0.4)] hover:border-white/18
        max-[768px]:rounded-[25px] max-[768px]:px-[10px] max-[768px]:pt-[13px] max-[768px]:pb-[8px]"
      :data-typing="typing || undefined"
      @submit.prevent="!busy && submit()"
      @click.self="focus"
    >
      <label class="sr-only" for="prompt">AI에게 메시지 보내기</label>
      <textarea
        id="prompt"
        ref="input"
        v-model="prompt"
        :readonly="typing"
        class="block h-[30px] max-h-[min(200px,30dvh)] min-h-[30px] w-full resize-none
          overflow-y-auto bg-transparent text-ink px-[7px] text-[16px]/[24px] outline-none
          placeholder:text-subtle short:max-h-[min(120px,22dvh)]"
        rows="1"
        placeholder="기업명이나 조건으로 찾아보세요 (예: 반도체 관련 코스피 기업)"
        @input="resizeInput"
        @keydown.enter="submitOnEnter"
      ></textarea>
      <div class="mt-[14px] flex justify-end max-[768px]:mt-[12px] short:mt-[6px]" @click.self="focus">
        <button
          class="grid size-[36px] place-items-center rounded-full bg-ink text-bg transition-[transform,background-color,color]
            duration-200 enabled:hover:scale-105 enabled:active:scale-95
            disabled:cursor-default disabled:bg-white/10 disabled:text-subtle pointer-coarse:size-[44px]"
          type="submit"
          :disabled="!prompt.trim() || busy"
          aria-label="메시지 보내기"
        >
          <svg class="size-[22px] fill-none stroke-current stroke-2" viewBox="0 0 24 24" aria-hidden="true"
            stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 20V4m-6 6 6-6 6 6" />
          </svg>
        </button>
      </div>
    </form>
  </div>
</template>
