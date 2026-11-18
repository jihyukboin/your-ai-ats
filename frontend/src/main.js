import { createSSRApp } from 'vue'
import App from './App.vue'

const state = document.getElementById('initial-state')
createSSRApp(App, state ? JSON.parse(state.textContent) : {}).mount('#app')
