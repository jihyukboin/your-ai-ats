<script setup>
import { nextTick, onMounted, onUnmounted, ref } from 'vue'

const prompt = ref('')
const input = ref(null)
const form = ref(null)
const feedback = ref('')

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
onUnmounted(() => observer?.disconnect())

function submitOnEnter(event) {
  if (event.shiftKey || event.isComposing) return
  event.preventDefault()
  form.value.requestSubmit()
}

function submit() {
  if (!prompt.value.trim()) return
  feedback.value = '현재 기업 탐색을 사용할 수 없습니다.'
}

async function reset() {
  prompt.value = ''
  feedback.value = ''
  await nextTick()
  resizeInput()
  input.value.focus()
}

function focus() {
  input.value.focus()
}

defineExpose({ reset, focus })
</script>

<template>
  <div class="w-full max-w-[816px] px-[24px] pb-[max(12px,env(safe-area-inset-bottom))] max-[768px]:px-[12px]">
    <form
      ref="form"
      class="cursor-text rounded-[28px] border border-line bg-white px-[13px] pt-[15px] pb-[9px]
        shadow-[0_2px_8px_#00000009] focus-within:border-[#818b99]
        max-[768px]:rounded-[25px] max-[768px]:px-[10px] max-[768px]:pt-[13px] max-[768px]:pb-[8px]"
      @submit.prevent="submit"
      @click.self="focus"
    >
      <label class="sr-only" for="prompt">AI에게 메시지 보내기</label>
      <textarea
        id="prompt"
        ref="input"
        v-model="prompt"
        class="block h-[30px] max-h-[min(200px,30dvh)] min-h-[30px] w-full resize-none
          overflow-y-auto bg-transparent px-[7px] text-[16px]/[24px] outline-none
          placeholder:text-[#707070] short:max-h-[min(120px,22dvh)]"
        rows="1"
        placeholder="기업명이나 조건으로 찾아보세요 (예: 반도체 관련 코스피 기업)"
        @input="resizeInput"
        @keydown.enter="submitOnEnter"
      ></textarea>
      <div class="mt-[14px] flex justify-end max-[768px]:mt-[12px] short:mt-[6px]" @click.self="focus">
        <button
          class="grid size-[36px] place-items-center rounded-full bg-ink text-white enabled:hover:opacity-80
            disabled:cursor-default disabled:bg-line pointer-coarse:size-[44px]"
          type="submit"
          :disabled="!prompt.trim()"
          aria-label="메시지 보내기"
        >
          <svg class="size-[22px] fill-none stroke-current stroke-2" viewBox="0 0 24 24" aria-hidden="true"
            stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 20V4m-6 6 6-6 6 6" />
          </svg>
        </button>
      </div>
    </form>
    <p class="mt-[11px] text-center text-[12px] text-muted" role="status">{{ feedback }}</p>
  </div>
</template>
