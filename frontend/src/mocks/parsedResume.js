// 백엔드 파싱 API가 준비되기 전까지 사용하는 목업 결과입니다.
export const PARSE_STEPS = ['문서 업로드', '텍스트 추출', '섹션 인식', '정보 구조화']

export const PARSED_SECTIONS = [
  {
    id: 'profile',
    title: '기본 정보',
    fields: [
      { label: '이름', value: '김싸피' },
      { label: '이메일', value: 'ssafy@example.com' },
      { label: '연락처', value: '010-1234-5678' },
      { label: '희망 직무', value: '백엔드 개발자' },
    ],
  },
  {
    id: 'education',
    title: '학력',
    items: [
      { title: '싸피대학교 컴퓨터공학과', meta: '2018.03 – 2024.02', sub: '학사 · 학점 3.9 / 4.5' },
    ],
  },
  {
    id: 'experience',
    title: '경력',
    items: [
      {
        title: '싸피테크 · 백엔드 인턴',
        meta: '2023.07 – 2023.12',
        bullets: ['주문 API 응답 시간 420ms → 180ms 개선', 'Redis 캐시 도입으로 DB 부하 35% 감소'],
      },
    ],
  },
  {
    id: 'projects',
    title: '프로젝트',
    items: [
      {
        title: 'AI 면접 코치',
        meta: '2024.01 – 2024.02',
        bullets: ['FastAPI 기반 음성 답변 분석 서버 구축', 'SSAFY 공통 프로젝트 우수상'],
      },
      {
        title: '실시간 공연 예매 플랫폼',
        meta: '2023.09 – 2023.10',
        bullets: ['대기열 시스템으로 동시 접속 5,000명 처리'],
      },
    ],
  },
  {
    id: 'skills',
    title: '기술 스택',
    tags: ['Python', 'FastAPI', 'Java', 'Spring Boot', 'PostgreSQL', 'Redis', 'Docker', 'AWS'],
  },
  {
    id: 'certificates',
    title: '자격증',
    items: [
      { title: '정보처리기사', meta: '2023.11' },
      { title: 'SQLD', meta: '2023.06' },
    ],
  },
]
