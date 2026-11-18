function applyRun(message, run) {
  message.phase = run.status === 'running' ? 'thinking' : run.status
  message.stages = run.stages
  message.text = run.text
  message.sources = run.sources
}

export async function restoreRuns(companyId, messages) {
  const response = await fetch(`/api/companies/${companyId}/analyses`)
  if (!response.ok) throw new Error('분석 기록 조회 실패')
  let complete = false
  for (const run of await response.json()) {
    messages.push({ id: run.id + '-user', role: 'user', started: run.started, text: run.role ? run.prompt + '\n지원 직무 · ' + run.role : run.prompt })
    const message = { id: run.id, role: 'assistant', started: run.started }
    applyRun(message, run)
    if (run.status === 'running') message.phase = 'snapshot'
    messages.push(message)
    complete ||= run.status === 'done'
  }
  return complete
}

export async function analyzeCompany(companyId, role, prompt, message) {
  const response = await fetch(`/api/companies/${companyId}/analyses`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ prompt, role }),
  })
  if (!response.ok) throw new Error('기업 분석 요청 실패')
  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader()
  let buffer = ''
  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    const lines = (buffer + value).split('\n')
    buffer = lines.pop()
    for (const line of lines) applyRun(message, JSON.parse(line))
  }
  if (message.phase === 'thinking') throw new Error('분석 연결이 종료되었습니다.')
}
