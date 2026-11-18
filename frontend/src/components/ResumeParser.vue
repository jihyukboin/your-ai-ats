<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { PARSE_STEPS, PARSED_SECTIONS } from '../mocks/parsedResume.js'
import ParsedSection from './ParsedSection.vue'
import ParseProgress from './ParseProgress.vue'

const STEP_MS = 900
const SECTION_MS = 420

const step = ref(0)
const shownSections = ref(0)
const parsing = computed(() => step.value < PARSE_STEPS.length)
const sections = ref(structuredClone(PARSED_SECTIONS))

// 목업 타임라인: 단계를 하나씩 완료한 뒤 섹션을 순서대로 보여줍니다.
const timers = []
onMounted(() => {
  PARSE_STEPS.forEach((_, index) => timers.push(setTimeout(() => (step.value = index + 1), (index + 1) * STEP_MS)))
  const start = PARSE_STEPS.length * STEP_MS + 350
  PARSED_SECTIONS.forEach((_, index) =>
    timers.push(setTimeout(() => (shownSections.value = index + 1), start + index * SECTION_MS)))
})
onUnmounted(() => timers.forEach(clearTimeout))
</script>

<template>
  <div class="w-full max-w-[816px] px-[24px] pt-[28px] pb-[max(32px,env(safe-area-inset-bottom))] max-[768px]:px-[12px]">
    <Transition
      leave-active-class="transition duration-300 ease-in"
      leave-to-class="opacity-0 scale-[0.98] blur-[4px]"
    >
      <ParseProgress v-if="parsing" :steps="PARSE_STEPS" :current="step" />
    </Transition>

    <div v-if="!parsing" class="mt-[20px] flex flex-col gap-[28px]">
      <template v-for="(section, index) in sections" :key="section.id">
        <ParsedSection v-if="index < shownSections" v-model="sections[index]" />
      </template>
    </div>
  </div>
</template>
