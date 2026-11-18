<script>
import MarkdownIt from 'markdown-it'
import cjkFriendly from 'markdown-it-cjk-friendly'
import { cleanUrl } from '../utils/sources.js'

const markdown = new MarkdownIt({ html: false }).use(cjkFriendly)

// 모든 링크는 새 탭으로 열고, 숫자만 있는 링크는 인용 번호 칩으로 표시합니다.
markdown.renderer.rules.link_open = (tokens, index, options, env, self) => {
  const token = tokens[index]
  token.attrSet('target', '_blank')
  token.attrSet('rel', 'noreferrer')
  if (/^\d+$/.test(tokens[index + 1]?.content ?? '') && tokens[index + 2]?.type === 'link_close') {
    token.attrJoin('class', 'citation')
    try {
      token.attrSet('title', new URL(token.attrGet('href')).hostname.replace(/^www\./, ''))
    } catch {}
  }
  return self.renderToken(tokens, index, options)
}
</script>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  source: { type: String, required: true },
  sources: { type: Array, default: () => [] },
})

// "([도메인](URL))" 형태의 인라인 출처를 출처 목록 번호로 바꿉니다.
const html = computed(() => {
  const urls = props.sources.map(item => item.url)
  const text = props.source.replace(/\s*\(\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)\)/g, (match, label, url) => {
    const number = urls.indexOf(cleanUrl(url)) + 1
    return number ? ` [${number}](${cleanUrl(url)})` : ` [${label}](${cleanUrl(url)})`
  })
  return markdown.render(text)
})
</script>

<template>
  <div class="markdown min-w-0 wrap-anywhere" v-html="html" />
</template>

<style scoped>
@reference "../styles/main.css";

.markdown { @apply text-[15px]/[1.8] text-ink/88; }
.markdown :deep(> :first-child) { @apply mt-0; }
.markdown :deep(:is(h1, h2, h3, h4, h5, h6)) { @apply font-semibold tracking-[-0.3px] text-ink; }
.markdown :deep(h1) { @apply mt-9 mb-3 text-[21px]; }
.markdown :deep(h2) { @apply mt-9 mb-3 text-[19px]; }
.markdown :deep(h3) { @apply mt-7 mb-2 text-[16.5px]; }
.markdown :deep(:is(h4, h5, h6)) { @apply mt-5 mb-1.5 text-[15px] text-muted; }
.markdown :deep(p) { @apply my-3; }
.markdown :deep(:is(ul, ol)) { @apply my-3 pl-[22px]; }
.markdown :deep(ul) { @apply list-disc; }
.markdown :deep(ol) { @apply list-decimal; }
.markdown :deep(li) { @apply my-1.5 pl-[2px] marker:text-subtle; }
.markdown :deep(li > :is(ul, ol)) { @apply my-1.5; }
.markdown :deep(li > p) { @apply my-1; }
.markdown :deep(strong) { @apply font-semibold text-ink; }
.markdown :deep(hr) { @apply my-8 border-line; }
.markdown :deep(blockquote) { @apply my-4 border-l-2 border-tint/60 pl-4 text-muted; }
.markdown :deep(a:not(.citation)) { @apply text-tint underline decoration-tint/40 underline-offset-[3px] hover:decoration-tint; }
.markdown :deep(a.citation) {
  @apply mx-[2px] inline-grid h-[18px] min-w-[18px] place-items-center rounded-full bg-white/8 px-[5px]
    align-[2px] text-[11px]/none font-medium text-muted no-underline tabular-nums transition-colors
    hover:bg-tint hover:text-white;
}
.markdown :deep(table) { @apply my-4 block max-w-full overflow-x-auto border-collapse text-[14px]; }
.markdown :deep(:is(th, td)) { @apply border-b border-line px-3 py-2 text-left; }
.markdown :deep(th) { @apply font-semibold text-ink; }
.markdown :deep(code) { @apply rounded-[6px] bg-white/7 px-[5px] py-[1px] font-mono text-[13px]; }
.markdown :deep(pre) { @apply my-4 overflow-x-auto rounded-[12px] bg-panel p-4; }
.markdown :deep(pre code) { @apply bg-transparent p-0; }
</style>
