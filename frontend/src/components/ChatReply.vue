<script setup>
import AgentReply from './AgentReply.vue'
import FitReport from './FitReport.vue'

defineProps({
  message: { type: Object, required: true },
  companyName: { type: String, default: '' },
  userName: { type: String, default: '' },
})
</script>

<template>
  <div class="flex gap-[14px] motion-safe:animate-rise">
    <span
      class="grid size-[30px] shrink-0 place-items-center rounded-full bg-[linear-gradient(135deg,var(--color-tint),#a78bfa,#f472b6)]
        shadow-[0_0_18px_rgb(167_139_250/0.35)]"
      aria-hidden="true"
    >
      <svg class="size-[16px] fill-white" :class="message.phase === 'thinking' && 'motion-safe:animate-spin motion-safe:[animation-duration:2.4s]'"
        viewBox="0 0 24 24">
        <path d="M12 2c.6 4.8 3.2 7.4 8 8-4.8.6-7.4 3.2-8 8-.6-4.8-3.2-7.4-8-8 4.8-.6 7.4-3.2 8-8Z" />
      </svg>
    </span>

    <FitReport v-if="message.kind === 'fit'" class="min-w-0 flex-1 pt-[1px]" :message="message"
      :company-name="companyName" :user-name="userName" :aria-busy="message.phase === 'thinking'" />
    <AgentReply v-else class="min-w-0 flex-1 pt-[1px]" :message="message" :aria-busy="message.phase === 'thinking'" />
  </div>
</template>
