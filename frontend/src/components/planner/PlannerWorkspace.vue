<script setup>
import { ref } from 'vue'
import PlannerChat from './PlannerChat.vue'
import PlanList from './PlanList.vue'
import LogList from './LogList.vue'
const tab = ref('대화')
const tabs = ['대화', '저장한 계획', '실행 로그']
</script>
<template>
  <div class="min-h-dvh">
    <header class="border-b border-line bg-sidebar">
      <div class="mx-auto flex max-w-4xl flex-wrap items-center justify-between gap-3 px-5 py-4">
        <a href="/" class="flex items-center gap-2 font-semibold"><img src="/your-ats.svg" alt="" width="28" height="28">Your ATS</a>
        <span class="text-sm text-muted">포트폴리오 준비 플래너</span>
      </div>
    </header>
    <main class="mx-auto max-w-4xl px-5 pb-12">
      <h1 class="sr-only">포트폴리오 준비 플래너</h1>
      <nav aria-label="플래너 메뉴" class="mb-6 flex gap-6 border-b border-line">
        <button v-for="item in tabs" :key="item" :aria-current="tab === item ? 'page' : null" class="border-b-2 border-transparent py-4 text-muted aria-[current=page]:border-tint aria-[current=page]:text-ink" @click="tab=item">{{ item }}</button>
      </nav>
      <PlannerChat v-show="tab === '대화'" />
      <PlanList v-if="tab === '저장한 계획'" />
      <LogList v-if="tab === '실행 로그'" />
    </main>
  </div>
</template>
