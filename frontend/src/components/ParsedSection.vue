<script setup>
import { computed, nextTick, ref, toRaw } from 'vue'

// 부모가 가진 섹션 데이터를 v-model로 받고, 편집 중에는 사본(draft)만 수정합니다.
const section = defineModel({ type: Object, required: true })
const draft = ref(null)
const panel = ref(null)
const editing = computed(() => draft.value !== null)
const data = computed(() => draft.value ?? section.value)
const tagInput = ref('')

const delay = index => ({ animationDelay: `${120 + index * 70}ms` })

async function edit() {
  draft.value = structuredClone(toRaw(section.value))
  await nextTick()
  panel.value.querySelector('input, textarea')?.focus()
}

function cancel() {
  draft.value = null
  tagInput.value = ''
}

function save() {
  const next = draft.value
  next.fields?.forEach(field => (field.value = field.value.trim()))
  if (next.items) {
    next.items = next.items
      .map(item => ({ ...item, bullets: item.bullets?.map(text => text.trim()).filter(Boolean) }))
      .filter(item => item.title.trim())
  }
  if (next.tags) next.tags = next.tags.filter(Boolean)
  section.value = next
  cancel()
}

function addItem() {
  draft.value.items.push({ title: '', meta: '', sub: '', bullets: [] })
  nextTick(() => panel.value.querySelector('li:last-of-type input')?.focus())
}

function addTag() {
  const tag = tagInput.value.trim()
  if (tag && !draft.value.tags.includes(tag)) draft.value.tags.push(tag)
  tagInput.value = ''
}
</script>

<template>
  <section class="motion-safe:animate-rise" :aria-labelledby="`section-${section.id}`" @keydown.esc="cancel">
    <div class="mb-[10px] flex items-end justify-between px-[4px]">
      <h2 :id="`section-${section.id}`" class="text-[20px]/[25px] font-semibold tracking-[-0.45px] text-ink">
        {{ section.title }}
      </h2>
      <div class="flex gap-[16px] text-[15px]">
        <template v-if="editing">
          <button class="text-muted hover:text-ink" type="button" @click="cancel">취소</button>
          <button class="font-semibold text-tint hover:opacity-80" type="button" @click="save">완료</button>
        </template>
        <button v-else class="text-tint hover:opacity-80" type="button" :aria-label="`${section.title} 편집`" @click="edit">
          편집
        </button>
      </div>
    </div>

    <div
      ref="panel"
      class="overflow-hidden rounded-[16px] bg-panel shadow-[inset_0_0_0_1px_var(--color-line)] transition-shadow duration-300"
      :class="editing && 'shadow-[inset_0_0_0_1px_var(--color-line),0_0_0_4px_rgb(10_132_255/0.14)]'"
    >
      <!-- 기본 정보: 라벨/값 행 -->
      <dl v-if="data.fields" class="divide-y divide-line">
        <div
          v-for="(field, index) in data.fields"
          :key="field.label"
          class="flex min-h-[48px] items-center gap-[16px] px-[16px] motion-safe:animate-rise"
          :style="delay(index)"
        >
          <dt class="w-[84px] shrink-0 text-[14px] text-muted">{{ field.label }}</dt>
          <dd class="min-w-0 flex-1 text-[15px]">
            <input v-if="editing" v-model="field.value" class="edit-input" :aria-label="field.label" />
            <span v-else class="block truncate">{{ field.value || '—' }}</span>
          </dd>
        </div>
      </dl>

      <!-- 기술 스택: 태그 -->
      <div v-else-if="data.tags" class="px-[16px] py-[14px]">
        <ul class="flex flex-wrap gap-[8px]">
          <li
            v-for="(tag, index) in data.tags"
            :key="tag"
            class="flex h-[30px] items-center gap-[4px] rounded-full bg-white/7 pr-[12px] pl-[12px] text-[13.5px] motion-safe:animate-rise"
            :class="editing && 'pr-[5px]'"
            :style="delay(index)"
          >
            {{ tag }}
            <button
              v-if="editing"
              class="grid size-[20px] place-items-center rounded-full text-muted hover:bg-white/10 hover:text-ink"
              type="button"
              :aria-label="`${tag} 삭제`"
              @click="data.tags.splice(index, 1)"
            >
              <svg class="size-[11px] fill-none stroke-current stroke-[2.4]" viewBox="0 0 24 24" aria-hidden="true" stroke-linecap="round">
                <path d="M6 6l12 12M18 6 6 18" />
              </svg>
            </button>
          </li>
        </ul>
        <input
          v-if="editing"
          v-model="tagInput"
          class="edit-input mt-[12px]"
          placeholder="기술 추가 후 Enter"
          aria-label="기술 추가"
          @keydown.enter.prevent="!$event.isComposing && addTag()"
        />
      </div>

      <!-- 학력/경력/프로젝트/자격증: 항목 행 -->
      <ul v-else class="divide-y divide-line">
        <li
          v-for="(item, index) in data.items"
          :key="index"
          class="flex gap-[12px] px-[16px] py-[14px] motion-safe:animate-rise"
          :style="delay(index)"
        >
          <button
            v-if="editing"
            class="mt-[7px] grid size-[22px] shrink-0 place-items-center rounded-full bg-danger text-white hover:opacity-85"
            type="button"
            :aria-label="`${item.title || '항목'} 삭제`"
            @click="data.items.splice(index, 1)"
          >
            <span class="h-[2px] w-[10px] rounded-full bg-current"></span>
          </button>

          <div v-if="editing" class="grid min-w-0 flex-1 grid-cols-[1fr_160px] gap-[8px] max-[768px]:grid-cols-1">
            <input v-model="item.title" class="edit-input font-medium" placeholder="제목" aria-label="제목" />
            <input v-model="item.meta" class="edit-input tabular-nums" placeholder="기간" aria-label="기간" />
            <input v-if="'sub' in item" v-model="item.sub" class="edit-input col-span-full" placeholder="세부 정보" aria-label="세부 정보" />
            <textarea
              v-if="item.bullets"
              class="edit-input col-span-full min-h-[64px] resize-none field-sizing-content"
              placeholder="주요 내용 (줄마다 하나씩)"
              aria-label="주요 내용"
              :value="item.bullets.join('\n')"
              @input="item.bullets = $event.target.value.split('\n')"
            ></textarea>
          </div>

          <div v-else class="min-w-0 flex-1">
            <div class="flex items-baseline justify-between gap-[12px]">
              <span class="text-[15px] font-medium">{{ item.title }}</span>
              <span class="shrink-0 text-[13px] text-subtle tabular-nums">{{ item.meta }}</span>
            </div>
            <p v-if="item.sub" class="mt-[3px] text-[13.5px] text-muted">{{ item.sub }}</p>
            <ul v-if="item.bullets?.length" class="mt-[8px] flex flex-col gap-[4px] text-[14px]/[1.55] text-muted">
              <li v-for="bullet in item.bullets" :key="bullet" class="flex gap-[10px]">
                <span class="mt-[9px] size-[4px] shrink-0 rounded-full bg-subtle"></span>
                {{ bullet }}
              </li>
            </ul>
          </div>
        </li>
        <li v-if="editing">
          <button class="flex h-[48px] w-full items-center gap-[12px] px-[16px] text-[15px] text-tint hover:bg-hover" type="button" @click="addItem">
            <span class="grid size-[22px] place-items-center rounded-full bg-tint text-[17px]/none text-white">+</span>
            {{ section.title }} 추가
          </button>
        </li>
        <li v-else-if="!data.items.length" class="px-[16px] py-[14px] text-[14px] text-subtle">항목이 없습니다</li>
      </ul>
    </div>
  </section>
</template>
