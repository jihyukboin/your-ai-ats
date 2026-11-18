<script setup>
import { nextTick, onMounted, ref } from 'vue'
import CompanyPanel from './components/CompanyPanel.vue'
import ResumeDropzone from './components/ResumeDropzone.vue'
import ResumeParser from './components/ResumeParser.vue'
import UserBadge from './components/UserBadge.vue'

const props = defineProps({
  companies: { type: Array, default: () => [] },
  listError: Boolean,
  activeCompanyId: { type: Number, default: null },
})

const dropzone = ref(null)
const resume = ref(null)

async function resetHome() {
  if (props.activeCompanyId !== null) {
    window.location.assign('/')
    return
  }
  resume.value = null
  await nextTick()
  dropzone.value.reset()
}

onMounted(() => {
  if (!window.matchMedia('(width < 960px)').matches) dropzone.value.focus()
})
</script>

<template>
  <div class="flex h-dvh min-h-0">
    <aside
      class="flex min-w-0 flex-[0_0_280px] flex-col overflow-hidden border-r border-line bg-sidebar px-[8px] max-sidebar:basis-[240px]"
      aria-label="사이드바"
    >
      <div class="-mx-[8px] flex flex-[0_0_64px] items-center border-b border-line px-[12px]">
        <button
          class="flex h-[40px] items-center gap-[8px] rounded-[9px] pr-[10px] hover:bg-hover
            pointer-coarse:h-[44px]"
          type="button"
          aria-label="Your ATS 홈"
          @click="resetHome"
        >
          <img src="/your-ats.svg" width="36" height="36" alt="" />
          <span class="text-[17px] font-semibold tracking-[-0.3px] whitespace-nowrap">Your ATS</span>
        </button>
      </div>
      <CompanyPanel :initial-companies="companies" :list-error="listError" :active-company-id="activeCompanyId" />
    </aside>

    <main class="relative flex min-w-0 flex-1 flex-col">
      <header
        class="absolute inset-x-0 top-0 z-1 flex h-[64px] items-center justify-center bg-bg/35 backdrop-blur-[1px]"
      >
        <UserBadge name="사용자" avatar="/avatar.webp" />
      </header>
      <div class="flex min-h-0 flex-1 flex-col items-center overflow-y-auto pt-[64px] scrollbar-thin">
        <ResumeParser v-if="resume" />
        <section
          v-else
          class="flex min-h-[110px] w-full shrink-0 basis-[calc(42%_-_25px)] flex-col
            items-center justify-end px-[24px] pb-[30px] text-center
            max-sidebar:basis-[38%] max-sidebar:pb-[24px] wide:basis-[calc(44%_-_25px)]
            short:min-h-0 short:basis-auto short:py-[clamp(8px,4dvh,20px)]"
          aria-labelledby="greeting"
        >
          <h1 id="greeting" class="text-[28px]/[1.5] font-[550] tracking-[-0.8px] max-sidebar:text-[25px]">
            이력서를 올려주세요
          </h1>
        </section>
        <ResumeDropzone v-if="!resume" ref="dropzone" @select="resume = $event" />
      </div>
    </main>
  </div>
</template>
