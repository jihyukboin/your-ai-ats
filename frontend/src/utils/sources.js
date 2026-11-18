// 출처 URL을 정리(추적 파라미터 제거·중복 제거)하고 화면에 보여줄 이름을 만듭니다.
// 사람이 읽을 수 있는 제목(띄어쓰기·한글 포함, ID처럼 보이지 않음)만 제목으로 씁니다.
const readable = name => /[\s가-힣]/.test(name) && !/^[\da-f\s]+$/i.test(name) && !/\d{6,}/.test(name)

export function cleanUrl(url) {
  try {
    const parsed = new URL(url)
    for (const key of [...parsed.searchParams.keys()]) if (key.startsWith('utm_')) parsed.searchParams.delete(key)
    return parsed.toString()
  } catch {
    return url
  }
}

function describe(url) {
  const parsed = new URL(url)
  const domain = parsed.hostname.replace(/^(www|m)\./, '')
  const segment = parsed.pathname.split('/').filter(Boolean).at(-1) ?? ''
  let name = ''
  try {
    name = decodeURIComponent(segment).replace(/\.\w+$/, '').replace(/[-_]+/g, ' ').trim()
  } catch {
    name = ''
  }
  return { url, domain, title: readable(name) ? name : domain }
}

export function toSources(urls = []) {
  const unique = [...new Set(urls.map(cleanUrl))]
  return unique.flatMap(url => {
    try {
      return [describe(url)]
    } catch {
      return []
    }
  })
}

export function monogramStyle(domain) {
  let hash = 0
  for (const char of domain) hash = (hash * 31 + char.charCodeAt(0)) % 360
  return { backgroundColor: `hsl(${hash} 38% 30%)` }
}
