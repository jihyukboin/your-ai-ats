<script setup>
defineProps({ steps: Array, current: Number })

const lineWidths = ['55%', '35%', '100%', '90%', '95%', '60%', '100%', '80%', '70%']
</script>

<template>
  <div class="flex items-center justify-center gap-[40px] py-[28px] max-[768px]:flex-col max-[768px]:gap-[24px]">
    <div
      class="relative h-[196px] w-[152px] shrink-0 overflow-hidden rounded-[14px] border border-line-strong
        bg-sidebar px-[16px] py-[18px] shadow-[0_12px_40px_rgb(0_0_0/0.45)]"
      aria-hidden="true"
    >
      <div
        v-for="(width, index) in lineWidths"
        :key="index"
        class="skeleton-line mb-[10px] h-[7px] rounded-full first:h-[10px] [&:nth-child(3)]:mt-[18px]"
        :style="{ width, animationDelay: `${index * 90}ms` }"
      ></div>
      <div class="pointer-events-none absolute inset-x-0 top-0 h-full motion-safe:animate-scan">
        <div class="h-[56px] bg-linear-to-b from-transparent to-focus/18"></div>
        <div class="h-[2px] bg-focus shadow-[0_0_14px_2px_rgb(229_33_46/0.7)]"></div>
      </div>
    </div>

    <ol class="flex min-w-[180px] flex-col gap-[14px]">
      <li
        v-for="(step, index) in steps"
        :key="step"
        class="flex items-center gap-[12px] text-[14px] transition-colors duration-300"
        :class="index <= current ? 'text-ink' : 'text-subtle'"
      >
        <span class="grid size-[22px] shrink-0 place-items-center">
          <svg
            v-if="index < current"
            class="size-[22px] text-focus motion-safe:animate-pop"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <circle cx="12" cy="12" r="11" class="fill-current" />
            <path d="m7.5 12.5 3 3 6-6.5" class="fill-none stroke-white stroke-[2.2]"
              stroke-linecap="round" stroke-linejoin="round" />
          </svg>
          <span
            v-else-if="index === current"
            class="size-[18px] rounded-full border-2 border-line-strong border-t-focus motion-safe:animate-spin"
          ></span>
          <span v-else class="size-[8px] rounded-full bg-line-strong"></span>
        </span>
        {{ step }}
      </li>
    </ol>
  </div>
</template>
