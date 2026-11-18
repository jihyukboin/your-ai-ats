<script setup>
import { onMounted, ref } from 'vue'

const message = ref('')
const pending = ref(true)

async function checkConnection() {
  pending.value = true
  message.value = '연결 확인 중…'

  try {
    const response = await fetch('/api/health', { cache: 'no-store' })
    if (!response.ok) throw new Error('Health check failed')
    const health = await response.json()
    if (health.status !== 'ok' || health.database !== 'sqlite') {
      throw new Error('Unexpected health response')
    }
    message.value = 'FastAPI와 SQLite에 연결되었습니다.'
  } catch {
    message.value = '연결에 실패했습니다. 백엔드 실행 상태를 확인해 주세요.'
  } finally {
    pending.value = false
  }
}

onMounted(checkConnection)
</script>

<template>
  <main>
    <h1>AI 코어 플래너</h1>
    <p role="status">{{ message }}</p>
    <button type="button" :disabled="pending" @click="checkConnection">연결 다시 확인</button>
  </main>
</template>

<style>
:root {
  font-family: system-ui, sans-serif;
  color: #162b24;
  background: #f4f7f5;
  line-height: 1.55;
}

main {
  max-width: 34rem;
  margin: clamp(2rem, 12vh, 8rem) auto;
  padding: 1.5rem;
}

h1 {
  margin: 0;
}

button {
  padding: 0.55rem 1rem;
  border: 1px solid #305e4d;
  border-radius: 0.4rem;
  background: #fff;
  color: #234638;
  font: inherit;
  cursor: pointer;
}

button:disabled {
  cursor: wait;
  opacity: 0.65;
}
</style>
