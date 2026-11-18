<script setup>
import { computed, ref } from 'vue'
import { toSources } from '../utils/sources.js'
import AgentActivity from './AgentActivity.vue'
import MarkdownContent from './MarkdownContent.vue'
import SourceList from './SourceList.vue'

const props = defineProps({ message: { type: Object, required: true } })

const sources = computed(() => toSources(props.message.sources))
const copied = ref(false)

async function copy() {
  await navigator.clipboard.writeText(props.message.text)
  copied.value = true
  setTimeout(() => (copied.value = false), 1500)
}
</script>

<template>
  <div class="flex flex-col gap-[18px]">
    <AgentActivity :stages="message.stages" :phase="message.phase" />

    <p v-if="message.error" class="text-[14px] text-danger" role="alert">{{ message.error }}</p>

    <template v-if="message.text && message.phase !== 'thinking'">
      <MarkdownContent class="motion-safe:animate-rise" :source="message.text" :sources="sources" />

      <div class="flex items-start gap-[6px] border-t border-line pt-[14px]">
        <SourceList class="min-w-0 flex-1" :sources="sources" />
        <button class="icon-button text-muted hover:text-ink" type="button" :aria-label="copied ? '복사됨' : '답변 복사'" @click="copy">
          <svg class="size-[17px] fill-none stroke-current stroke-2" viewBox="0 0 24 24" aria-hidden="true"
            stroke-linecap="round" stroke-linejoin="round">
            <path v-if="copied" d="m5 12.5 4.5 4.5L19 7.5" />
            <template v-else>
              <rect x="9" y="9" width="11" height="11" rx="2.5" />
              <path d="M15 9V6.5A2.5 2.5 0 0 0 12.5 4h-6A2.5 2.5 0 0 0 4 6.5v6A2.5 2.5 0 0 0 6.5 15H9" />
            </template>
          </svg>
        </button>
      </div>
    </template>
  </div>
</template>
