<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import PlannerWorkspace from './components/planner/PlannerWorkspace.vue'
import CompanyChat from './components/CompanyChat.vue'
import CompanyPanel from './components/CompanyPanel.vue'
import CompanyStepper from './components/CompanyStepper.vue'
import ResumeDropzone from './components/ResumeDropzone.vue'
import ResumeParser from './components/ResumeParser.vue'
import UserBadge from './components/UserBadge.vue'

const props = defineProps({
  plannerPage: Boolean,
  companies: { type: Array, default: () => [] },
  listError: Boolean,
  savedResume: Object,
  userProfile: Object,
  resumeError: Boolean,
  activeCompanyId: { type: Number, default: null },
})

const dropzone = ref(null)
const chat = ref(null)
const stepCurrent = ref(0)
const resume = ref(null)
const profile = ref(props.userProfile ?? null)
const savedResume = ref(props.savedResume ?? null)
const uploadNumber = ref(0)
const replacing = ref(false)
const busy = ref(false)
const activeCompany = computed(() => props.companies.find(company => company.id === props.activeCompanyId))

function startUpload(file, replace = false) {
  uploadNumber.value++
  replacing.value = replace
  restoreError.value = false
  busy.value = true
  resume.value = file
}

function showResult(result) {
  profile.value = { name: result.name, avatar: result.avatar }
  if (props.activeCompanyId === null) savedResume.value = result
  else resume.value = null
  busy.value = false
}

const restoreError = ref(props.resumeError)

async function retryUpload() {
  if (props.activeCompanyId !== null) {
    window.location.assign('/')
    return
  }
  restoreError.value = false
  if (savedResume.value) uploadNumber.value++
  resume.value = null
  await nextTick()
  dropzone.value?.reset()
}

onMounted(() => {
  if (!window.matchMedia('(width < 960px)').matches) dropzone.value?.focus()
})
</script>

<template>
  <PlannerWorkspace v-if="plannerPage" />
  <div v-else class="flex h-dvh min-h-0">
    <aside
      class="flex min-w-0 flex-[0_0_280px] flex-col overflow-hidden border-r border-line bg-sidebar px-[8px] max-sidebar:basis-[240px]"
      aria-label="사이드바"
    >
      <div class="-mx-[8px] flex flex-[0_0_64px] items-center border-b border-line px-[12px]">
        <a
          class="flex h-[40px] items-center gap-[8px] rounded-[9px] pr-[10px] hover:bg-hover
            pointer-coarse:h-[44px]"
          href="/"
          aria-label="Your ATS 홈"
        >
          <img src="/your-ats.svg" width="36" height="36" alt="" />
          <span class="text-[17px] font-semibold tracking-[-0.3px] whitespace-nowrap">Your ATS</span>
        </a>
      </div>
      <a href="/workspace/planner" class="mx-1 mt-3 rounded-lg px-2 py-3 text-sm font-semibold text-tint hover:bg-hover">포트폴리오 준비 플래너 ↗</a>
      <CompanyPanel :initial-companies="companies" :list-error="listError" :active-company-id="activeCompanyId" />
      <ResumeDropzone compact :disabled="busy" @select="startUpload($event, true)" />
    </aside>

    <main class="relative flex min-w-0 flex-1 flex-col">
      <header
        class="absolute inset-x-0 top-0 z-1 flex h-[64px] items-center justify-center bg-bg/35 backdrop-blur-[1px]"
      >
        <UserBadge :name="profile?.name || '사용자'" :avatar="profile?.avatar || '/avatar.webp'" />
      </header>
      <CompanyStepper
        v-if="activeCompany"
        class="mt-[64px] shrink-0"
        :company-name="activeCompany.name"
        :user-name="profile?.name || '사용자'"
        :current="stepCurrent"
        @select="(prompt, index) => chat?.send(prompt, index)"
      />
      <div
        class="flex min-h-0 flex-1 flex-col items-center overflow-y-auto scrollbar-thin"
        :class="activeCompany ? 'pt-0' : 'pt-[64px]'"
      >
        <p v-if="restoreError" role="alert" class="mt-4 text-muted">저장된 이력서를 불러오지 못했습니다. 새로고침해 다시 시도해주세요.</p>
        <ResumeParser v-if="resume || savedResume" :key="uploadNumber" :file="resume" :replace="replacing" :saved-resume="resume ? null : savedResume" @parsed="showResult" @failed="busy = false" @reset="retryUpload" />
        <section
          v-else-if="activeCompanyId === null"
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
        <CompanyChat
          :company-id="activeCompanyId"
          v-if="activeCompany"
          v-show="!resume"
          ref="chat"
          :company-name="activeCompany.name"
          :user-name="profile?.name || '사용자'"
          @complete="step => step === stepCurrent && stepCurrent++"
        />
        <ResumeDropzone v-if="activeCompanyId === null && !resume && !savedResume" ref="dropzone" @select="startUpload($event)" />
      </div>
    </main>
  </div>
</template>
