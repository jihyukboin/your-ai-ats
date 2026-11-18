// 3단계 자기소개서 전략 API(/cover-letters)와 통신합니다. 결과는 마크다운 보고서라 1단계 답변 화면을 그대로 씁니다.
function applyLetter(message, run) {
  message.phase = run.status === 'running' ? 'thinking' : run.status
  message.stages = run.stages
  message.text = run.text
  message.sources = run.sources
  message.error = run.error
  message.started = run.started
}

export async function restoreLetters(companyId, messages) {
  const response = await fetch(`/api/companies/${companyId}/cover-letters`)
  if (!response.ok) throw new Error('자기소개서 전략 기록 조회 실패')
  let complete = false
  for (const run of await response.json()) {
    messages.push({ id: run.id + '-user', role: 'user', started: run.started, text: run.prompt || `자기소개서 전략\n지원 직무 · ${run.role}` })
    const message = { id: run.id, role: 'assistant' }
    applyLetter(message, run)
    if (run.status === 'running') message.phase = 'snapshot'
    messages.push(message)
    complete ||= run.status === 'done'
  }
  return complete
}

async function latestFit(companyId) {
  const response = await fetch(`/api/companies/${companyId}/fit-analyses`)
  if (!response.ok) throw new Error('2단계 적합도 기록을 불러오지 못했습니다.')
  const fit = (await response.json()).find(run => run.status === 'done')
  if (!fit) throw new Error('2단계 이력서 적합도 분석을 먼저 완료해주세요.')
  return fit
}

export async function writeLetter(companyId, prompt, message) {
  const fit = await latestFit(companyId)
  const response = await fetch(`/api/companies/${companyId}/cover-letters`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ fit_id: fit.id, prompt }),
  })
  if (!response.ok) {
    const detail = await response.json().then(body => body.detail, () => null)
    throw new Error(typeof detail === 'string' ? detail : '자기소개서 전략 요청 실패')
  }
  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader()
  let buffer = ''
  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    const lines = (buffer + value).split('\n')
    buffer = lines.pop()
    for (const line of lines) if (line.trim()) applyLetter(message, JSON.parse(line))
  }
  if (message.phase === 'thinking') throw new Error('분석 연결이 종료되었습니다.')
}
