import { readFile } from 'node:fs/promises'
import tailwindcss from '@tailwindcss/vite'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'
import { companyPath } from './src/utils/companyPath.js'

const backend = process.env.PLANNER_BACKEND_URL || 'http://127.0.0.1:8000'

function pageMiddleware(loadTemplate, loadRenderer) {
  return async (request, response, next) => {
    const path = request.url?.split('?')[0]
    const accept = request.headers.accept ?? '*/*'
    const plannerPage = path === '/workspace/planner'
    if (request.method !== 'GET' || (!plannerPage && !/^\/[^/]*$/.test(path ?? '')) ||
        (!accept.includes('text/html') && accept !== '*/*')) return next()

    let companyName
    try {
      companyName = decodeURIComponent(path.slice(1))
    } catch {
      return next()
    }

    try {
      let props = { plannerPage }
      if (!plannerPage) {
        try {
          const result = await fetch(backend + '/api/companies', { signal: AbortSignal.timeout(4000) })
          if (!result.ok) throw new Error('Company list unavailable')
          props = { companies: await result.json() }
        } catch {
          props = { companies: [], listError: true }
        }
        const home = path === '/' || path === '/index.html'
        let activeCompany
        if (!home && !props.listError) {
          const id = companyName.match(/-(\d+)$/)?.[1]
          const byId = props.companies.find(company => String(company.id) === id)
          if (byId && companyName === `${byId.name}-${byId.id}`) {
            activeCompany = byId
          } else {
            const legacy = props.companies.filter(company => company.name === companyName)
            const target = legacy.length === 1 ? legacy[0] : byId
            if (!target) return next()
            response.writeHead(302, { Location: companyPath(target) + request.url.slice(path.length) })
            return response.end()
          }
        }
        props.activeCompanyId = activeCompany?.id ?? null

        try {
          const result = await fetch(backend + '/api/resumes/latest', { signal: AbortSignal.timeout(4000) })
          if (!result.ok) throw new Error('Resume unavailable')
          const resume = await result.json()
          if (resume) {
            props.userProfile = { name: resume.name, avatar: resume.avatar }
            if (path === '/' || path === '/index.html') props.savedResume = resume
          }
        } catch {
          props.resumeError = true
        }
      }
      const [template, { render }] = await Promise.all([loadTemplate(path), loadRenderer()])
      const state = JSON.stringify(props).replaceAll('<', '\\u003c')
      const markup = await render(props)
      response.setHeader('Cache-Control', 'no-store')
      response.setHeader('Content-Type', 'text/html; charset=utf-8')
      response.end(template.replace('<!--ssr-outlet-->', () => markup)
        .replace('</body>', () => `<script id="initial-state" type="application/json">${state}</script></body>`))
    } catch (error) {
      next(error)
    }
  }
}

export default defineConfig({
  plugins: [vue(), tailwindcss(), {
    name: 'render-page',
    configureServer(server) {
      server.middlewares.use(pageMiddleware(
        async path => server.transformIndexHtml(path, await readFile('index.html', 'utf8')),
        () => server.environments.ssr.runner.import('/src/entry-server.js')
      ))
    },
    configurePreviewServer(server) {
      server.middlewares.use(pageMiddleware(
        () => readFile('dist/client/index.html', 'utf8'),
        () => import(/* @vite-ignore */ new URL('./dist/server/entry-server.js', import.meta.url).href)
      ))
    }
  }],
  preview: { proxy: { '/api': backend } },
  build: { outDir: 'dist/client' },
  server: { host: '127.0.0.1', port: 5173, proxy: { '/api': backend } },
})
