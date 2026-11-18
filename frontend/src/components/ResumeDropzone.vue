<script setup>
import { ref } from 'vue'

const ACCEPT = '.pdf,application/pdf'
const MAX_BYTES = 10 * 1024 * 1024
const emit = defineEmits(['select'])

const input = ref(null)
const dragging = ref(false)
const feedback = ref('')

function select(files) {
  const picked = files?.[0]
  if (!picked) return
  if (!/\.pdf$/i.test(picked.name)) {
    feedback.value = 'PDF 파일만 올릴 수 있습니다.'
    return
  }
  if (picked.size > MAX_BYTES) {
    feedback.value = '10MB 이하의 파일만 올릴 수 있습니다.'
    return
  }
  feedback.value = ''
  emit('select', picked)
}

function onChange(event) {
  select(event.target.files)
  event.target.value = ''
}

function onDragLeave(event) {
  if (!event.currentTarget.contains(event.relatedTarget)) dragging.value = false
}

function onDrop(event) {
  dragging.value = false
  select(event.dataTransfer.files)
}

function reset() {
  feedback.value = ''
  input.value.focus()
}

function focus() {
  input.value.focus()
}

defineExpose({ reset, focus })
</script>

<template>
  <div class="w-full max-w-[816px] px-[24px] pb-[max(12px,env(safe-area-inset-bottom))] max-[768px]:px-[12px]">
    <label
      class="flex min-h-[220px] cursor-pointer flex-col items-center justify-center gap-[10px] rounded-[28px]
        border-2 border-dashed px-[24px] py-[32px] text-center transition-colors
        focus-within:border-focus/55 focus-within:shadow-[0_0_0_3px_rgb(229_33_46/0.1)] hover:bg-hover max-[768px]:min-h-[180px] max-[768px]:rounded-[25px]
        short:min-h-[140px] short:py-[16px]"
      :class="dragging ? 'border-focus bg-focus/8' : 'border-line-strong'"
      @dragenter.prevent="dragging = true"
      @dragover.prevent
      @dragleave="onDragLeave"
      @drop.prevent="onDrop"
    >
      <input ref="input" class="sr-only" type="file" :accept="ACCEPT" @change="onChange" />
      <svg class="size-[36px] fill-none stroke-current stroke-[1.65] text-muted" viewBox="0 0 24 24"
        aria-hidden="true" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 16V4m-5 5 5-5 5 5M4 16v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" />
      </svg>
      <span class="text-[16px] font-medium">파일을 끌어다 놓거나 클릭해서 선택하세요</span>
      <span class="text-[13px] text-subtle">PDF · 최대 10MB</span>
    </label>

    <p class="mt-[11px] text-center text-[12px] text-muted" role="status">{{ feedback }}</p>
  </div>
</template>
