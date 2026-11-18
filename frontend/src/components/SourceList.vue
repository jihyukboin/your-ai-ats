<script setup>
import { ref } from 'vue'
import { monogramStyle } from '../utils/sources.js'

defineProps({ sources: { type: Array, required: true } })
const open = ref(false)
</script>

<template>
  <div v-if="sources.length">
    <button
      class="flex h-[32px] items-center gap-[8px] rounded-full bg-white/6 pr-[12px] pl-[5px] text-[13px] text-muted
        transition-colors hover:bg-white/10 hover:text-ink"
      type="button"
      :aria-expanded="open"
      @click="open = !open"
    >
      <span class="flex -space-x-[6px]" aria-hidden="true">
        <span v-for="item in sources.slice(0, 4)" :key="item.url"
          class="grid size-[22px] place-items-center rounded-full text-[10px] font-bold text-white uppercase ring-2 ring-bg"
          :style="monogramStyle(item.domain)">{{ item.domain[0] }}</span>
      </span>
      출처 {{ sources.length }}개
    </button>

    <div class="grid transition-[grid-template-rows] duration-300 ease-out" :class="open ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]'">
      <div class="overflow-hidden" :inert="!open">
        <ol class="grid grid-cols-2 gap-[8px] pt-[12px] max-[768px]:grid-cols-1">
          <li v-for="(item, index) in sources" :key="item.url">
            <a :href="item.url" target="_blank" rel="noreferrer" :title="item.url"
              class="flex h-full items-center gap-[10px] rounded-[12px] bg-white/4 px-[11px] py-[9px] transition-colors hover:bg-white/8">
              <span class="grid size-[26px] shrink-0 place-items-center rounded-[8px] text-[11px] font-bold text-white uppercase"
                :style="monogramStyle(item.domain)" aria-hidden="true">{{ item.domain[0] }}</span>
              <span class="min-w-0 flex-1">
                <span class="block truncate text-[13px] text-ink">{{ item.title }}</span>
                <span v-if="item.title !== item.domain" class="block truncate text-[11.5px] text-subtle">{{ item.domain }}</span>
              </span>
              <span class="shrink-0 text-[11px] text-subtle tabular-nums">{{ index + 1 }}</span>
            </a>
          </li>
        </ol>
      </div>
    </div>
  </div>
</template>
