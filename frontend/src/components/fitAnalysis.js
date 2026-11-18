// 2단계 이력서 적합도 분석 API(/fit-analyses)와 통신합니다.
async function errorMessage(response, fallback) {
  try {
    const { detail } = await response.json()
    return typeof detail === 'string' ? detail : fallback
  } catch {
    return fallback
  }
}

export function applyFit(message, run) {
  message.phase = run.status === 'running' ? 'thinking' : run.status
  message.stages = run.stages
  message.run = run
  message.started = run.started
}

export async function restoreFits(companyId, messages) {
  const response = await fetch(`/api/companies/${companyId}/fit-analyses`)
  if (!response.ok) throw new Error('적합도 기록 조회 실패')
  let complete = false
  for (const run of (await response.json()).reverse()) {
    messages.push({ id: run.id + '-user', role: 'user', started: run.started, text: `이력서 적합도 분석\n지원 직무 · ${run.role}` })
    const message = { id: run.id, role: 'assistant', kind: 'fit' }
    applyFit(message, run)
    if (run.status === 'running') message.phase = 'snapshot'
    messages.push(message)
    complete ||= run.status === 'done'
  }
  return complete
}

// 가장 최근에 끝난 1단계 분석을 기준으로 평가합니다(백엔드가 같은 직무를 요구합니다).
async function latestAnalysis(companyId) {
  const response = await fetch(`/api/companies/${companyId}/analyses`)
  if (!response.ok) throw new Error('1단계 분석 기록을 불러오지 못했습니다.')
  const analysis = (await response.json()).findLast(run => ['done', 'partial'].includes(run.status) && run.role)
  if (!analysis) throw new Error('지원 직무를 입력해 1단계 기업/직무 분석을 먼저 완료해주세요.')
  return analysis
}

export async function evaluateFit(companyId, message) {
  const analysis = await latestAnalysis(companyId)
  const response = await fetch(`/api/companies/${companyId}/fit-analyses`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ analysis_id: analysis.id, role: analysis.role }),
  })
  if (!response.ok) throw new Error(await errorMessage(response, '적합도 분석 요청 실패'))
  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader()
  let buffer = ''
  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    const lines = (buffer + value).split('\n')
    buffer = lines.pop()
    for (const line of lines) if (line.trim()) applyFit(message, JSON.parse(line))
  }
  if (message.phase === 'thinking') throw new Error('분석 연결이 종료되었습니다.')
}
