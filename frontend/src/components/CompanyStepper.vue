<script setup>
import { computed } from 'vue'

const props = defineProps({
  companyName: { type: String, required: true },
  userName: { type: String, required: true },
  current: { type: Number, default: 0 },
})

defineEmits(['select'])

const steps = computed(() => {
  const company = props.companyName
  const user = props.userName
  return [
    {
      title: `${company} 기업/직무 분석`,
      prompt: `${company}의 사업 구조와 최근 실적·주요 이슈, 인재상을 정리하고, 지원 직무에서 요구하는 핵심 역량과 우대 경험을 분석해 주세요.`,
    },
    {
      title: `${user} 이력서와 ${company} 적합도 분석`,
      prompt: `제 이력서를 ${company}의 직무 요구사항과 비교해서 강점, 보완이 필요한 부분, 전체 적합도를 근거와 함께 평가해 주세요.`,
    },
    {
      title: `${company} 자기소개서 전략`,
      prompt: `${company} 자기소개서 문항별로 제 경험 중 어떤 사례를 어떤 메시지로 풀어내면 좋을지 전략과 개요를 제안해 주세요.`,
    },
  ]
})

const status = index => (index < props.current ? 'done' : index === props.current ? 'current' : 'upcoming')
const statusLabel = { done: '완료', current: '진행 중', upcoming: '대기' }
</script>

<template>
  <nav class="w-full border-b border-line bg-bg/80 backdrop-blur-md" aria-label="분석 진행 단계">
    <ol class="grid grid-cols-3">
      <li
        v-for="(step, index) in steps"
        :key="index"
        class="relative min-w-0 motion-safe:animate-rise"
        :style="{ animationDelay: `${index * 90}ms` }"
        :aria-current="status(index) === 'current' ? 'step' : undefined"
      >
        <button
          class="group flex w-full min-w-0 items-center gap-[12px] px-[24px] py-[14px] text-left transition-colors
            duration-200 enabled:hover:bg-hover enabled:active:bg-active disabled:cursor-default
            focus-visible:-outline-offset-2 max-sidebar:gap-[10px] max-sidebar:px-[14px]"
          type="button"
          :disabled="index > 0 && status(index) === 'done'"
          :aria-label="status(index) === 'done' ? undefined : `${step.title} 질문하기`"
          @click="$emit('select', step.prompt, index)"
        >
          <span class="absolute inset-x-0 bottom-[-1px] h-[2px] overflow-hidden" aria-hidden="true">
            <span
              class="block h-full origin-left transition-transform duration-700 ease-out"
              :class="{
                'scale-x-100 bg-ink/70': status(index) === 'done',
                'scale-x-100 bg-[linear-gradient(90deg,var(--color-tint),#a78bfa,#f472b6)]': status(index) === 'current',
                'scale-x-0': status(index) === 'upcoming',
              }"
            ></span>
          </span>

          <span
            class="grid size-[28px] shrink-0 place-items-center rounded-full text-[13px] font-semibold tabular-nums
              transition-colors duration-300"
            :class="{
              'bg-ink text-bg': status(index) === 'done',
              'bg-tint text-white shadow-[0_0_0_4px_rgb(10_132_255/0.18)]': status(index) === 'current',
              'bg-white/6 text-subtle shadow-[inset_0_0_0_1px_var(--color-line-strong)]': status(index) === 'upcoming',
            }"
          >
            <svg v-if="status(index) === 'done'" class="size-[15px] fill-none stroke-current stroke-[2.6]" viewBox="0 0 24 24"
              aria-hidden="true" stroke-linecap="round" stroke-linejoin="round">
              <path d="m5 12.5 4.5 4.5L19 7.5" />
            </svg>
            <template v-else>{{ index + 1 }}</template>
          </span>

          <span class="min-w-0 flex-1">
            <span
              class="grid text-[12px] font-medium *:col-start-1 *:row-start-1 *:transition-opacity *:duration-200"
              :class="status(index) === 'current' ? 'text-tint' : 'text-subtle'"
            >
              <span :class="status(index) !== 'done' && 'fine-hover:group-hover:opacity-0'">
                {{ index + 1 }}단계 · {{ statusLabel[status(index)] }}
              </span>
              <span v-if="status(index) !== 'done'" class="text-tint opacity-0 fine-hover:group-hover:opacity-100" aria-hidden="true">
                눌러서 바로 질문하기
              </span>
            </span>
            <span
              class="mt-[2px] block truncate text-[14.5px] font-medium tracking-[-0.2px]"
              :class="status(index) === 'upcoming' ? 'text-muted' : 'text-ink'"
              :title="step.title"
            >
              {{ step.title }}
            </span>
          </span>

          <svg v-if="index < steps.length - 1" class="size-[16px] shrink-0 fill-none stroke-current stroke-2 text-subtle
            max-[1100px]:hidden" viewBox="0 0 24 24" aria-hidden="true" stroke-linecap="round" stroke-linejoin="round">
            <path d="m9 6 6 6-6 6" />
          </svg>
        </button>
      </li>
    </ol>
  </nav>
</template>
