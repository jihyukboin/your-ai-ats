// 2단계 적합도 평가 결과를 1단계 답변과 같은 리서치 보고서(마크다운)로 바꿉니다.
import { cleanUrl } from './sources.js'

const VERDICT_LABEL = { direct: '직접 일치', related: '유사 경험', unconfirmed: '미기재' }

const hasAdvice = (text = '') => Boolean(text.trim()) && !/^(없음|해당 없음|n\/a)\.?$/i.test(text.trim())
const quoteText = (quote = '') => quote.split('\n')
  .map(line => line.replace(/\*\*/g, '').replace(/^\s*[-*•]\s*/, '').trim())
  .filter(Boolean)
  .join(' / ')

export function fitReport(result, { company, user, role }) {
  const items = result.items
  const sources = [...new Set(items.map(item => item.requirement.source).filter(Boolean).map(cleanUrl))]
  const cite = url => (url ? ` [${sources.indexOf(cleanUrl(url)) + 1}](${cleanUrl(url)})` : '')
  const count = verdict => items.filter(item => item.verdict === verdict).length
  const [direct, related, unconfirmed] = ['direct', 'related', 'unconfirmed'].map(count)
  const evidence = item => (item.evidence ? `${item.evidence.section_title} · “${item.evidence.quote}”` : '이력서에서 확인되지 않음')

  const lines = [
    '## 요약',
    `${user}님의 이력서를 ${company} **${role}** 직무 요구사항 ${items.length}개와 비교했습니다. ` +
      `**${direct}개**는 이력서에서 직접 확인되고, **${related}개**는 유사 경험으로 확인되며, **${unconfirmed}개**는 이력서에서 확인되지 않았습니다.`,
    result.basis === 'company_job'
      ? `평가 기준은 ${company}의 채용 공고에 명시된 필수·우대 요건입니다.`
      : `${company}의 공식 채용 공고에서 필수·우대 요건을 확인하지 못해, 직무 일반 요건을 기준으로 평가했습니다.`,
    '',
    '| 판정 | 항목 수 | 비율 |',
    '|---|---:|---:|',
    ...[['직접 일치', direct], ['유사 경험', related], ['미기재', unconfirmed]]
      .map(([label, value]) => `| ${label} | ${value} | ${items.length ? Math.round((value / items.length) * 100) : 0}% |`),
    '',
    '---',
    '',
    '## 1. 강점',
    ...(direct ? items.filter(item => item.verdict === 'direct').map(item => `- **${item.requirement.text}** — ${evidence(item)}`)
      : ['- 이력서에서 직접 확인된 요구사항이 없습니다.']),
    '',
    '## 2. 보완이 필요한 부분',
    ...(unconfirmed + related
      ? items.filter(item => item.verdict !== 'direct')
        .map(item => `- **${item.requirement.text}** (${VERDICT_LABEL[item.verdict]})${hasAdvice(item.suggestion) ? ` — ${item.suggestion}` : ''}`)
      : ['- 모든 요구사항이 이력서에서 직접 확인됐습니다.']),
    '',
    '---',
    '',
    '## 3. 요구사항별 상세 분석',
    ...items.flatMap((item, index) => [
      '',
      `### 3.${index + 1} ${item.requirement.text}`,
      `- **판정**: ${VERDICT_LABEL[item.verdict]}`,
      `- **기업 요구**: ${quoteText(item.requirement.quote) || '직무 일반 요건'}${cite(item.requirement.source)}`,
      `- **이력서 근거**: ${evidence(item)}`,
      `- **판단 근거**: ${item.reason}`,
      ...(hasAdvice(item.suggestion) ? [`- **보완 제안**: ${item.suggestion}`] : []),
    ]),
    '',
    '---',
    '',
    '> 미기재는 역량이 없다는 뜻이 아니라 이력서에서 확인되지 않았다는 의미입니다. 보완 제안을 참고해 관련 경험을 구체적으로 기재해 보세요.',
  ]
  return { text: lines.join('\n'), sources }
}
