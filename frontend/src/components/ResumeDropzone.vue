<script setup>
import { ref } from 'vue'

const ACCEPT = '.pdf,.docx'
const MAX_BYTES = 10 * 1024 * 1024

const input = ref(null)
const file = ref(null)
const dragging = ref(false)
const feedback = ref('')

function select(files) {
  const picked = files?.[0]
  if (!picked) return
  if (!/\.(pdf|docx)$/i.test(picked.name)) {
    feedback.value = 'PDF 또는 DOCX 파일만 올릴 수 있습니다.'
    return
  }
  if (picked.size > MAX_BYTES) {
    feedback.value = '10MB 이하의 파일만 올릴 수 있습니다.'
    return
  }
  file.value = picked
  feedback.value = ''
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

function formatSize(bytes) {
  return bytes < 1024 * 1024 ? `${Math.ceil(bytes / 1024)}KB` : `${(bytes / 1024 / 1024).toFixed(1)}MB`
}

function reset() {
  file.value = null
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
      <span class="text-[13px] text-subtle">PDF, DOCX · 최대 10MB</span>
    </label>

    <div
      v-if="file"
      class="mt-[12px] flex items-center gap-[10px] rounded-[16px] border border-line-strong bg-sidebar px-[14px] py-[10px]"
    >
      <span class="min-w-0 flex-1 truncate text-[14px]">{{ file.name }}</span>
      <span class="shrink-0 text-[13px] text-muted">{{ formatSize(file.size) }}</span>
      <button class="icon-button text-muted" type="button" aria-label="선택한 파일 제거" @click="reset">
        <svg class="size-[18px] fill-none stroke-current stroke-2" viewBox="0 0 24 24" aria-hidden="true"
          stroke-linecap="round">
          <path d="M6 6l12 12M18 6 6 18" />
        </svg>
      </button>
    </div>
    <p class="mt-[11px] text-center text-[12px] text-muted" role="status">{{ feedback }}</p>
  </div>
</template>
