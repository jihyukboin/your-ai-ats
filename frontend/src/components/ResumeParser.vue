<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import ParsedSection from './ParsedSection.vue'
import ParseProgress from './ParseProgress.vue'

const props = defineProps({ file: Object, savedResume: Object, replace: Boolean })
const emit = defineEmits(['parsed', 'reset', 'failed'])
const PARSE_STEPS = ['문서 업로드', '텍스트 추출', '섹션 인식', '정보 구조화']
const step = ref(0)
const result = ref(props.savedResume ?? null)
const error = ref('')
const controller = new AbortController()
onUnmounted(() => controller.abort())

onMounted(async () => {
  if (result.value) return
  const body = new FormData()
  body.append('file', props.file)
  try {
    const response = await fetch(props.replace ? '/api/resumes/latest' : '/api/resumes', { method: props.replace ? 'PUT' : 'POST', body, signal: controller.signal })
    if (!response.ok) throw new Error((await response.json()).detail)
    const reader = response.body.pipeThrough(new TextDecoderStream()).getReader()
    let buffer = ''
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      const lines = (buffer + value).split('\n')
      buffer = lines.pop()
      for (const line of lines) {
        const event = JSON.parse(line)
        if (event.error) throw new Error(event.error)
        if (event.step !== undefined) step.value = event.step
        if (event.result) {
          result.value = event.result
          emit('parsed', event.result)
        }
      }
    }
    if (!result.value) throw new Error('결과를 받기 전에 연결이 종료되었습니다.')
  } catch (cause) {
    if (!controller.signal.aborted) {
      error.value = cause.message
      emit('failed')
    }
  }
})

async function save(index, section) {
  const { id, ...data } = section
  error.value = ''
  try {
    const response = await fetch(`/api/resumes/${result.value.id}/sections/${id}`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
    })
    if (!response.ok) throw new Error()
    result.value.sections[index] = await response.json()
  } catch {
    error.value = '변경 사항을 저장하지 못했습니다.'
  }
}
</script>

<template>
  <div class="w-full max-w-[816px] px-[24px] pt-[28px] pb-[max(32px,env(safe-area-inset-bottom))] max-[768px]:px-[12px]">
    <Transition
      leave-active-class="transition duration-300 ease-in"
      leave-to-class="opacity-0 scale-[0.98] blur-[4px]"
    >
      <ParseProgress v-if="!result && !error" :steps="PARSE_STEPS" :current="step" />
    </Transition>

    <p v-if="error" role="alert" class="text-center text-muted">
      {{ error }}
      <button v-if="!result" class="ml-2 text-tint" @click="$emit('reset')">{{ replace ? '돌아가기' : '다시 업로드' }}</button>
    </p>
    <div v-if="result" class="mt-[20px] flex flex-col gap-[28px]">
      <template v-for="(section, index) in result.sections" :key="section.id">
        <ParsedSection :model-value="section" @update:model-value="save(index, $event)" />
      </template>
    </div>
  </div>
</template>
